# herbalapp/models.py
from collections import deque
from decimal import Decimal

from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

from herbalapp.mlm_engine_binary import (
    calculate_member_binary_income_for_day,
    determine_rank_from_bv,
)

# ==========================================================
# AUTO ID GENERATOR (Legacy fallback)
# ==========================================================
def generate_auto_id():
    """
    Generates rocky001, rocky002, rocky003...
    Uses the Member table directly.
    This is a fallback if RockCounter is not used.
    """
    from herbalapp.models import Member

    last = Member.objects.order_by('-id').first()
    if not last:
        return "rocky001"

    last_id = last.auto_id.replace("rocky", "")
    new_number = int(last_id) + 1
    return f"rocky{new_number:03d}"


# ==========================================================
# AUTO COUNTER FOR ROCKY IDs (Recommended)
# ==========================================================
class RockCounter(models.Model):
    """
    A safe, atomic counter for generating Rocky IDs.
    Prevents race conditions when multiple members register at once.
    """
    name = models.CharField(max_length=50, unique=True)
    last = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name}:{self.last}"


# ==========================================================
# MEMBER MODEL (MAIN GENEALOGY TREE)
# ==========================================================
class Member(models.Model):
    # -------------------------
    # BASIC DETAILS
    # -------------------------
    member_id = models.CharField(max_length=20, unique=True)
    auto_id = models.CharField(max_length=20, unique=True, blank=True, null=True)

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    activation_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=False)

    total_bv = models.IntegerField(default=0)
    rank = models.CharField(max_length=100, default="", blank=True)

    total_left_bv = models.IntegerField(default=0)
    total_right_bv = models.IntegerField(default=0)
    left_new_today = models.IntegerField(default=0)
    right_new_today = models.IntegerField(default=0)

    left_cf = models.IntegerField(default=0)   # carry forward
    right_cf = models.IntegerField(default=0)
    binary_income = models.IntegerField(default=0)
    repurchase_wallet = models.IntegerField(default=0)

    # -------------------------
    # IDENTIFICATION / ADDRESS
    # -------------------------
    aadhar = models.CharField(max_length=20, blank=True, null=True)
    aadhar_number = models.CharField(max_length=20, null=True, blank=True)
    place = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, null=True, blank=True)
    taluk = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.CharField(max_length=10, null=True, blank=True)

    # -------------------------
    # MLM RELATIONSHIP
    # -------------------------
    # Direct sponsor (Add member form-ல sponsor_id யாரோ அவர்)
    sponsor = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="direct_downlines",
    )

    # Placement (binary tree left/right)
    left_member = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="placed_on_left_of",
    )
    right_member = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="placed_on_right_of",
    )

    # Node side relative to its upline (for BV / tree rendering)
    side = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        choices=[("left", "Left"), ("right", "Right")],
    )

    # -------------------------
    # BINARY ENGINE STATE
    # -------------------------
    left_cf = models.IntegerField(default=0)
    right_cf = models.IntegerField(default=0)

    # Lifetime eligibility (1:2 or 2:1)
    binary_eligible = models.BooleanField(default=False)
    binary_eligible_date = models.DateTimeField(null=True, blank=True)

    # Lifetime first 1:1 pair completed?
    has_completed_first_pair = models.BooleanField(default=False)

    # -------------------------
    # META / STOCK LEVEL
    # -------------------------
    from datetime import date
    joined_date = models.DateField(default=date.today)

    # Stock point level (for commission)
    level = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[
            ("district", "District Stock Point"),
            ("taluk", "Taluk Gallery"),
            ("pincode", "Pincode Home Shoppe"),
        ],
    )

    def __str__(self):
        return f"{self.auto_id or self.member_id or self.id} - {self.name}"

    # ==========================================================
    # AUTO ID GENERATOR (SAFE SEQUENCE with RockCounter)
    # ==========================================================
    def save(self, *args, **kwargs):
        # MEMBER_ID (rocky001, rocky002...)
        if not self.member_id:
            with transaction.atomic():
                counter, _ = RockCounter.objects.select_for_update().get_or_create(name='member')
                counter.last += 1
                self.member_id = f"rocky{counter.last:03d}"
                counter.save()

        # AUTO_ID (separate safe sequence)
        if not self.auto_id:
            with transaction.atomic():
                counter, _ = RockCounter.objects.select_for_update().get_or_create(name='auto_id')
                counter.last += 1
                self.auto_id = f"rocky{counter.last:03d}"
                counter.save()

        super().save(*args, **kwargs)

    # ==========================================================
    # SIMPLE HELPERS
    # ==========================================================
    def has_left(self):
        return self.left_member is not None

    def has_right(self):
        return self.right_member is not None

    # ==========================================================
    # PYRAMID TREE (JSON) - for UI
    # ==========================================================
    def get_pyramid_tree(self):
        def build(member):
            if not member:
                return None
            return {
                "auto_id": member.auto_id,
                "name": member.name,
                "side": member.side,
                # package UI-க்காக activation_amount-ஐ package ஆக காட்டுகிறோம்
                "package": str(member.activation_amount),
                "children": [build(member.left_member), build(member.right_member)],
            }

        return build(self)

    # ==========================================================
    # REPURCHASE BV LAST MONTH
    # ==========================================================
    def last_month_bv(self):
        from datetime import timedelta

        today = timezone.now()
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)

        repurchase_orders = Order.objects.filter(
            member=self,
            status="Paid",
            created_at__date__gte=first_day_last_month,
            created_at__date__lte=last_day_last_month,
        )

        total_bv = sum(
            (o.product.bv_value * o.quantity) for o in repurchase_orders
        ) if repurchase_orders else Decimal('0.00')

        return Decimal(total_bv)

    # ==========================================================
    # FULL BV CALCULATION (REPURCHASE ONLY, SUBTREE)
    # ==========================================================
    def calculate_bv(self):
        """
        Returns BV info for this member and full downline:
        - self_bv: only this member's repurchase BV
        - left_bv: total repurchase BV in left leg
        - right_bv: total repurchase BV in right leg
        - total_bv: sum of all above
        - matched_bv: min(left_bv, right_bv)
        """
        visited = set()
        queue = deque([self])

        left_bv = Decimal('0.00')
        right_bv = Decimal('0.00')

        # Self repurchase BV
        rep_orders_self = Order.objects.filter(member=self, status="Paid")
        self_bv = sum(
            (o.product.bv_value * o.quantity) for o in rep_orders_self
        ) if rep_orders_self else Decimal('0.00')

        while queue:
            member = queue.popleft()

            if not member or member.id in visited:
                continue
            visited.add(member.id)

            # Skip root for leg aggregation
            if member != self:
                rep_orders = Order.objects.filter(member=member, status="Paid")
                member_bv = sum(
                    (o.product.bv_value * o.quantity) for o in rep_orders
                ) if rep_orders else Decimal('0.00')

                # Leg is determined relative to root
                # We trust member.side as stored when placing in tree
                if member.side == 'left':
                    left_bv += Decimal(member_bv)
                elif member.side == 'right':
                    right_bv += Decimal(member_bv)

            if member.left_member:
                queue.append(member.left_member)
            if member.right_member:
                queue.append(member.right_member)

        total_bv = Decimal(self_bv) + left_bv + right_bv

        return {
            "self_bv": Decimal(self_bv),
            "left_bv": left_bv,
            "right_bv": right_bv,
            "total_bv": total_bv,
            "matched_bv": min(left_bv, right_bv),
        }

    # ==========================================================
    # BV COUNTS FOR LEFT / RIGHT (repurchase only, direct legs)
    # ==========================================================
    def get_bv_counts(self):
        """
        Simple left/right BV from immediate children.
        Uses calculate_bv() starting at left_member and right_member.
        """
        def resolve_bv(root_member):
            if not root_member:
                return Decimal('0.00')
            data = root_member.calculate_bv()
            return Decimal(data.get("self_bv", Decimal('0.00'))) + \
                   Decimal(data.get("left_bv", Decimal('0.00'))) + \
                   Decimal(data.get("right_bv", Decimal('0.00')))

        left_bv = resolve_bv(self.left_member)
        right_bv = resolve_bv(self.right_member)
        return (left_bv, right_bv)

    # ==========================================================
    # DAILY NEW MEMBERS (SPONSOR-BASED)
    # ==========================================================
    def get_new_members_today_count(self):
        today = timezone.now().date()
        return Member.objects.filter(sponsor=self, joined_date=today).count()

    # ==========================================================
    # STOCK COMMISSION TOTAL
    # ==========================================================
    def get_commission_total(self):
        district_total = Commission.objects.filter(
            member=self,
            commission_type="district"
        ).aggregate(Sum('commission_amount'))["commission_amount__sum"] or Decimal('0.00')

        taluk_total = Commission.objects.filter(
            member=self,
            commission_type="taluk"
        ).aggregate(Sum('commission_amount'))["commission_amount__sum"] or Decimal('0.00')

        pincode_total = Commission.objects.filter(
            member=self,
            commission_type="pincode"
        ).aggregate(Sum('commission_amount'))["commission_amount__sum"] or Decimal('0.00')

        return Decimal(district_total) + Decimal(taluk_total) + Decimal(pincode_total)

    # ==========================================================
    # RANK CALCULATION (USING determine_rank_from_bv)
    # ==========================================================
    def calculate_rank(self):
        """
        Uses matched repurchase BV only:
        matched_bv = min(left_bv, right_bv)
        Then applies determine_rank_from_bv(bv) from mlm_engine_binary.
        """
        bv_data = self.calculate_bv()
        matched_bv = bv_data["matched_bv"]

        result = determine_rank_from_bv(int(matched_bv))
        if not result:
            return

        title, monthly, months = result
        # Instance attributes (not DB fields) – safe
        self.current_rank = title
        self.salary = Decimal(monthly)
        self.rank_reward = Decimal(monthly) * Decimal(months)
        self.rank_assigned_at = timezone.now()
        self.save()

    # ==========================================================
    # BINARY ENGINE WRAPPER (PER DAY) – NEW ENGINE COMPATIBLE
    # ==========================================================
    def run_binary_engine_for_day(self, left_joins_today: int, right_joins_today: int):
        """
        Rocky Herbals – FINAL DAILY ENGINE WRAPPER (CORRECTED)

        Handles:
            ✅ Binary pairs, CF before/after
            ✅ Eligibility + first pair tracking
            ✅ Sponsor bonus (one-time, on first paid pair)
            ✅ Flashout → repurchase_wallet
            ✅ Rank title & monthly salary
            ✅ BV snapshot (left/right)
            ✅ DailyIncomeReport (binary + sponsor + salary)

        NOTE:
        - Sponsor bonus is given ONCE, when the FIRST paid pair happens (has_completed_first_pair flips).
        - DailyIncomeReport.sponsor_income is ALWAYS read from SponsorIncome table (no missed credit).
        """

        from datetime import date
        from decimal import Decimal
        from django.db.models import Sum
        from django.utils import timezone
        from herbalapp.models import DailyIncomeReport, SponsorIncome
        from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day, determine_rank_from_bv

        # ---- 0. Snapshot current state ----
        left_cf_before = self.left_cf
        right_cf_before = self.right_cf
        was_first_pair_completed_before = self.has_completed_first_pair

        # ---- 1. Run core binary engine ----
        result = calculate_member_binary_income_for_day(
            left_joins_today=left_joins_today,
            right_joins_today=right_joins_today,
            left_cf_before=left_cf_before,
            right_cf_before=right_cf_before,
            binary_eligible=self.binary_eligible,
        )

        # Expected keys in result:
        #   left_cf_after, right_cf_after,
        #   binary_pairs, binary_income,
        #   repurchase_wallet_bonus,
        #   flashout_units, washed_pairs,
        #   new_binary_eligible, became_eligible_today

        # ---- 2. Eligibility flags ----
        if result.get("new_binary_eligible") and not self.binary_eligible:
            self.binary_eligible = True
            self.binary_eligible_date = timezone.now()

        # First paid pair in lifetime?
        if result.get("binary_pairs", 0) > 0 and not self.has_completed_first_pair:
            self.has_completed_first_pair = True

        # ---- 3. Update CF + binary income + repurchase wallet ----
        self.left_cf = result.get("left_cf_after", left_cf_before)
        self.right_cf = result.get("right_cf_after", right_cf_before)

        binary_income_today = int(result.get("binary_income", 0) or 0)
        self.binary_income = (self.binary_income or 0) + binary_income_today

        repurchase_bonus_today = int(result.get("repurchase_wallet_bonus", 0) or 0)
        self.repurchase_wallet = (self.repurchase_wallet or 0) + repurchase_bonus_today

        self.save()

        # ---- 4. Sponsor income (one-time, on first paid pair) ----
        sponsor_bonus_today = 0

        # Give sponsor bonus when:
        #   - this member has a sponsor
        #   - at least one binary pair was paid TODAY
        #   - BEFORE today, first pair was NOT completed
        if (
            self.sponsor
            and result.get("binary_pairs", 0) > 0
            and not was_first_pair_completed_before
        ):
            SponsorIncome.objects.create(
                sponsor=self.sponsor,
                child=self,
                amount=Decimal("500.00"),
                date=date.today(),
            )
            sponsor_bonus_today = 500  # for log/understanding only (not used directly in report)

        # ---- 5. Rank & Monthly Salary (based on matched repurchase BV) ----
        rank_title = ""
        monthly_salary = 0

        bv_data = self.calculate_bv()  # {self_bv, left_bv, right_bv, total_bv, matched_bv}
        matched_bv = int(bv_data.get("matched_bv", 0))

        rank_info = determine_rank_from_bv(matched_bv)
        if rank_info:
            rank_title, monthly_salary, months = rank_info
            self.rank = rank_title
            # if you have rank_monthly_salary field, update it:
            if hasattr(self, "rank_monthly_salary"):
                self.rank_monthly_salary = monthly_salary
            self.save()

        # ---- 6. Daily Income Report (create/update) ----
        report, created = DailyIncomeReport.objects.get_or_create(
            member=self,
            date=date.today(),
            defaults={}
        )

        # Basic joins & CF movement
        report.left_joins = left_joins_today
        report.right_joins = right_joins_today

        report.left_cf_before = left_cf_before
        report.right_cf_before = right_cf_before
        report.left_cf_after = self.left_cf
        report.right_cf_after = self.right_cf

        # Binary payout
        report.binary_pairs_paid = result.get("binary_pairs", 0)
        report.binary_income = Decimal(binary_income_today)

        # Flashout → repurchase wallet
        report.flashout_units = result.get("flashout_units", 0)
        report.flashout_wallet_income = Decimal(repurchase_bonus_today)

        # Washed pairs
        report.washed_pairs = result.get("washed_pairs", 0)

        # BV snapshots
        report.total_left_bv = int(bv_data.get("left_bv", 0))
        report.total_right_bv = int(bv_data.get("right_bv", 0))

        # ✅ ALWAYS PULL SPONSOR INCOME FROM TABLE (no more 0.00 issues)
        today_sponsor_income = SponsorIncome.objects.filter(
            sponsor=self,
            date=date.today()
        ).aggregate(total=Sum('amount'))['total'] or 0

        report.sponsor_income = Decimal(today_sponsor_income)

        # Salary & rank
        report.salary_income = Decimal(monthly_salary)
        report.rank_title = rank_title

        # Total income = binary + sponsor + salary
        report.total_income = (
            report.binary_income +
            report.sponsor_income +
            report.salary_income
        )

        report.save()

# ==========================================================
# PAYMENT MODEL
# ==========================================================
class Payment(models.Model):
    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Pending', 'Pending'),
        ('Cancelled', 'Cancelled'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.name} - {self.status} - {self.amount}"


# ==========================================================
# INCOME MODEL (Corrected & Production‑Ready)
# ==========================================================
class Income(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)

    joining_package = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('3000.00'))
    binary_pairs = models.IntegerField(default=0)

    binary_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    sponsor_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Correct name (matches your plan)
    flash_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    salary_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"Income for {self.member.name} on {self.date}"


# ==========================================================
# SPONSOR INCOME MODEL
# ==========================================================
class SponsorIncome(models.Model):
    sponsor = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="sponsor_incomes")
    child = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="child_sponsor_incomes")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"Sponsor {self.sponsor.member_id} from {self.child.member_id} - {self.amount}"


# ==========================================================
# COMMISSION MODEL
# ==========================================================
class Commission(models.Model):
    COMM_TYPES = [
        ('district', 'District Stock Point (7%)'),
        ('taluk', 'Taluk Gallery (5%)'),
        ('pincode', 'Pincode Home Shoppe (3%)'),
    ]
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    commission_type = models.CharField(max_length=20, choices=COMM_TYPES)
    percentage = models.DecimalField(max_digits=4, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.name} - {self.commission_type} - {self.commission_amount}"


# ==========================================================
# PRODUCT MODEL
# ==========================================================
class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    mrp = models.DecimalField(max_digits=12, decimal_places=2)
    bv_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Product code like RH001, RH002...
    product_id = models.CharField(max_length=10, unique=True, editable=False, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.product_id:
            last_product = Product.objects.order_by('-id').first()
            if last_product and last_product.product_id:
                last_num = int(last_product.product_id.replace("RH", ""))
                new_num = last_num + 1
            else:
                new_num = 1
            self.product_id = f"RH{new_num:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.product_id}) - ₹{self.mrp} - BV: {self.bv_value}"


# ==========================================================
# ORDER MODEL (Corrected & Production‑Ready)
# ==========================================================
class Order(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    quantity = models.IntegerField(default=1)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)

    status = models.CharField(
        max_length=20,
        choices=[
            ("Paid", "Paid"),
            ("Pending", "Pending"),
            ("Cancelled", "Cancelled")
        ],
        default="Pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """
        Ensures total_amount is ALWAYS correct:
        total_amount = product.mrp * quantity
        """
        if self.product and self.quantity:
            self.total_amount = self.product.mrp * self.quantity

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} - {self.member.name}"


# ==========================================================
# RECORD MODELS
# ==========================================================
class IncomeRecord(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.name} - {self.type} - {self.amount}"


class CommissionRecord(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    level = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.name} - Level {self.level}"


class BonusRecord(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    type = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.name} - {self.type}"


# ==========================================================
# RANK REWARD MODELS
# ==========================================================
class RankReward(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="rank_rewards")
    rank_title = models.CharField(max_length=50)

    left_bv_snapshot = models.BigIntegerField()
    right_bv_snapshot = models.BigIntegerField()

    monthly_income = models.BigIntegerField()
    duration_months = models.IntegerField()

    start_date = models.DateField(default=timezone.now)
    months_paid = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    def credit_monthly_income(self):
        # Stop income after duration completed
        if not self.active or self.months_paid >= self.duration_months:
            self.active = False
            self.save(update_fields=["active"])
            return False

        # Add payout to main wallet (dynamic attribute if field not declared)
        self.member.main_wallet = getattr(self.member, "main_wallet", Decimal('0.00')) + Decimal(self.monthly_income)
        self.member.save()

        # Log payout
        RankPayoutLog.objects.create(
            member=self.member,
            rank_reward=self,
            amount=self.monthly_income,
            paid_on=timezone.now().date()
        )

        # Increase month count
        self.months_paid += 1
        if self.months_paid >= self.duration_months:
            self.active = False

        self.save(update_fields=["months_paid", "active"])
        return True

    def __str__(self):
        return f"{self.member.auto_id} - {self.rank_title}"


class RankPayoutLog(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="rank_payout_logs")
    rank_reward = models.ForeignKey(RankReward, on_delete=models.CASCADE, related_name="payout_logs")
    amount = models.BigIntegerField()
    paid_on = models.DateField()

    def __str__(self):
        return f"{self.member.auto_id} - {self.rank_reward.rank_title} - {self.amount} on {self.paid_on}"


class DailyIncomeReport(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    date = models.DateField()

    left_joins = models.IntegerField(default=0)
    right_joins = models.IntegerField(default=0)

    left_cf_before = models.IntegerField(default=0)
    right_cf_before = models.IntegerField(default=0)
    left_cf_after = models.IntegerField(default=0)
    right_cf_after = models.IntegerField(default=0)

    binary_pairs_paid = models.IntegerField(default=0)
    binary_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    flashout_units = models.IntegerField(default=0)
    flashout_wallet_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    washed_pairs = models.IntegerField(default=0)

    total_left_bv = models.BigIntegerField(default=0)
    total_right_bv = models.BigIntegerField(default=0)

    salary_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    rank_title = models.CharField(max_length=100, null=True, blank=True)

    sponsor_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_income = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        unique_together = ('member', 'date')

    def __str__(self):
        return f"Daily Report for {self.member.name} on {self.date}"

