# herbalapp/models.py
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from collections import deque

# ==========================================================
# AUTO COUNTER FOR ROCKY IDs
# ==========================================================
class RockCounter(models.Model):
    name = models.CharField(max_length=50, unique=True)
    last = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name}:{self.last}"


# ==========================================================
# MEMBER MODEL (MAIN – MLM ENGINE SAFE)
# ==========================================================
class Member(models.Model):

    # -------------------------
    # SYSTEM ID
    # -------------------------
    auto_id = models.CharField(max_length=20, unique=True)

    # -------------------------
    # BASIC DETAILS
    # -------------------------
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    activation_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    is_active = models.BooleanField(default=False)

    lifetime_pairs = models.IntegerField(default=0)  # track total completed pairs for eligibility

    def update_lifetime_pairs(self, new_pairs=1):
        self.lifetime_pairs += new_pairs
        self.save(update_fields=['lifetime_pairs'])


    # -------------------------
    # BUSINESS VOLUME & RANK
    # -------------------------
    total_bv = models.IntegerField(default=0)
    rank = models.CharField(max_length=100, blank=True, default="")

    total_left_bv = models.IntegerField(default=0)
    total_right_bv = models.IntegerField(default=0)

    # -------------------------
    # ADDRESS / KYC
    # -------------------------
    aadhar = models.CharField(max_length=20, blank=True, null=True)
    aadhar_number = models.CharField(max_length=20, blank=True, null=True)
    place = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    taluk = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)

    # =====================================================
    # 🔥 BINARY TREE (FOR TREE DISPLAY & PAIR CALCULATION)
    # =====================================================
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='children'
    )

    side = models.CharField(
        max_length=5,
        choices=[('left', 'Left'), ('right', 'Right')],
        null=True,
        blank=True
    )

    # ❌ REMOVED: left_child / right_child (BUG ROOT CAUSE)

    # =====================================================
    # SPONSOR TREE (FOR SPONSOR INCOME)
    # =====================================================
    sponsor = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sponsored_members'
    )

    # =====================================================
    # PLACEMENT TREE (FOR YOUR RULES)
    # =====================================================
    placement = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='placement_downline'
    )

    # -------------------------
    # TIMESTAMP
    # -------------------------
    created_at = models.DateTimeField(auto_now_add=True)

    # =====================================================
    # 🔑 HELPER METHODS (TREE SAFE)
    # =====================================================
    def left_child(self):
        return Member.objects.filter(parent=self, side='left').first()

    def right_child(self):
        return Member.objects.filter(parent=self, side='right').first()

    def has_pair(self):
        return self.left_child() and self.right_child()

    def __str__(self):
        return f"{self.auto_id} - {self.name}"

    # -------------------------
    # PACKAGE / RANK
    # -------------------------
    package = models.CharField(
        max_length=10,
        choices=[('Gold', 'Gold'), ('Silver', 'Silver'), ('Bronze', 'Bronze')],
        default='Bronze'
    )
    current_rank = models.CharField(max_length=50, null=True, blank=True)
    rank_assigned_at = models.DateTimeField(null=True, blank=True)

    # -------------------------
    # ACCOUNT FIELDS
    # -------------------------
    joined_date = models.DateField(default=timezone.now)
    active = models.BooleanField(default=True)

    # -------------------------
    # BV / RANK REWARD FIELDS
    # (Repurchase BV only)
    # -------------------------
    bv = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    rank_reward = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # -------------------------
    # WALLETS
    # -------------------------
    main_wallet = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    repurchase_wallet = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    flash_wallet = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    # -------------------------
    # INCOME / COUNTERS
    # -------------------------
    binary_pairs = models.IntegerField(default=0)
    binary_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    parent_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    sponsor_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Flash bonus (from binary flashouts)
    flash_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Stock commission (district / taluk / pincode)
    stock_commission = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Salary income (from rank)
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # -------------------------
    # BINARY ELIGIBILITY + CARRY FORWARD
    # -------------------------
    binary_eligible = models.BooleanField(default=False)
    binary_eligible_date = models.DateTimeField(null=True, blank=True)

    left_cf = models.IntegerField(default=0)
    right_cf = models.IntegerField(default=0)

    left_join_count = models.IntegerField(default=0)
    right_join_count = models.IntegerField(default=0)

    left_new_today = models.IntegerField(default=0)
    right_new_today = models.IntegerField(default=0)
    # BINARY CARRY FORWARD
    left_carry_forward = models.IntegerField(default=0)
    right_carry_forward = models.IntegerField(default=0)

    # DAILY JOIN TRACKING
    left_joins_today = models.IntegerField(default=0)
    right_joins_today = models.IntegerField(default=0)


    # -------------------------
    # STOCK POINT LEVEL (for commission)
    # district / taluk / pincode / None
    # -------------------------
    level = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[
            ("district", "District Stock Point"),
            ("taluk", "Taluk Gallery"),
            ("pincode", "Pincode Home Shoppe"),
        ]
    )

    # -------------------------
    # STRING REPRESENTATION
    # -------------------------
    def __str__(self):
        return f"{self.auto_id or self.auto_id or self.id} - {self.name}"

    # ==========================================================
    # AUTO ID GENERATOR (SAFE SEQUENCE with RockCounter)
    # ==========================================================
    def save(self, *args, **kwargs):
        # AUTO_ID (rocky001, rocky002...)
        if not self.auto_id:
            with transaction.atomic():
                counter, _ = RockCounter.objects.select_for_update().get_or_create(name='member')
                counter.last += 1
                self.auto_id = f"rocky{counter.last:03d}"
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
        return self.left_child is not None

    def has_right(self):
        return self.right_child is not None

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
                "package": member.package,
                "children": [build(member.left_child), build(member.right_child)],
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

            if member.left_child:
                queue.append(member.left_child)
            if member.right_child:
                queue.append(member.right_child)

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
        Uses calculate_bv() starting at left_child and right_child.
        """
        def resolve_bv(root_member):
            if not root_member:
                return Decimal('0.00')
            data = root_member.calculate_bv()
            return Decimal(data.get("self_bv", Decimal('0.00'))) + \
                   Decimal(data.get("left_bv", Decimal('0.00'))) + \
                   Decimal(data.get("right_bv", Decimal('0.00')))

        left_bv = resolve_bv(self.left_child)
        right_bv = resolve_bv(self.right_child)
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
        from django.db.models import Sum

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
        self.current_rank = title
        self.salary = Decimal(monthly)
        self.rank_reward = Decimal(monthly) * Decimal(months)
        self.rank_assigned_at = timezone.now()
        self.save()

    # ==========================================================
    # BINARY ENGINE WRAPPER (PER DAY)
    # ==========================================================


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
from decimal import Decimal
from django.db import models

class Income(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)

    joining_package = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('3000.00'))
    binary_pairs = models.IntegerField(default=0)

    binary_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    sponsor_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # ✅ Correct name (matches your binary engine + Member.flash_bonus)
    flash_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    salary_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"Income for {self.member.name} on {self.date}"
    class Meta:
        unique_together = ("member", "date")

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
from decimal import Decimal
from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    mrp = models.DecimalField(max_digits=12, decimal_places=2)
    bv_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # 🔹 Add this new field here
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
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="earned_commissions"
    )
    source_member = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_commissions"
    )
    level = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


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

    left_bv_snapshot = models.BigIntegerField()    # BV count at rank achieved time
    right_bv_snapshot = models.BigIntegerField()

    monthly_income = models.BigIntegerField()      # Example 5000/10000/25000/50k etc
    duration_months = models.IntegerField()        # 12, 24, 36 months (plan based)

    start_date = models.DateField(default=timezone.now)
    months_paid = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    def credit_monthly_income(self):
        # Stop income after duration completed
        if not self.active or self.months_paid >= self.duration_months:
            self.active = False
            self.save(update_fields=["active"])
            return False

        # Add payout to main wallet
        self.member.main_wallet = getattr(self.member, "main_wallet", Decimal('0.00')) + Decimal(self.monthly_income)
        self.member.save(update_fields=["main_wallet"])

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


# ==========================================================
# DAILY INCOME REPORT TABLE (Version-2 Engine Compatible)
# ==========================================================
from decimal import Decimal
from django.db import models
from herbalapp.models import Member  # Make sure Member is imported

class DailyIncomeReport(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    date = models.DateField()

    # Join counts
    left_joins = models.IntegerField(default=0)
    right_joins = models.IntegerField(default=0)

    # Carry forward before/after
    left_cf_before = models.IntegerField(default=0)
    right_cf_before = models.IntegerField(default=0)
    left_cf_after = models.IntegerField(default=0)
    right_cf_after = models.IntegerField(default=0)

    # Binary income
    binary_pairs_paid = models.IntegerField(default=0)
    binary_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Flashout income (repurchase wallet)
    flashout_units = models.IntegerField(default=0)
    flashout_wallet_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Washout (no income)
    washed_pairs = models.IntegerField(default=0)

    # BV snapshots (repurchase only)
    total_left_bv = models.BigIntegerField(default=0)
    total_right_bv = models.BigIntegerField(default=0)

    # Salary + rank
    salary_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    rank_title = models.CharField(max_length=100, null=True, blank=True)

    # Sponsor income
    sponsor_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Total income
    total_income = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        unique_together = ('member', 'date')
        ordering = ['-date', 'member']  # Optional: newest first

    def __str__(self):
        return f"Daily Report for {self.member.name} on {self.date}"

