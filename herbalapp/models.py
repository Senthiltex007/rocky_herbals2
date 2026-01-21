# herbalapp/models.py
from django.db import models, transaction
from django.utils import timezone
from decimal import Decimal
from collections import deque
from django.core.exceptions import ValidationError
from herbalapp.utils.auto_id import generate_auto_id  # ✅ new auto_id logic

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
    auto_id = models.CharField(max_length=20, unique=True)
    member_id = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        default="",
        help_text="Optional secondary ID"
    )

    class Meta:
        db_table = "herbalapp_member"   # ✅ explicit table name
        ordering = ["name"]             # ✅ default ordering in queries

    # =========================
    # ROOT DELETE PROTECTION
    # =========================
    def delete(self, *args, **kwargs):
        if self.auto_id in ["rocky001", "rocky002"]:
            raise ValidationError("ROOT members cannot be deleted")
        super().delete(*args, **kwargs)


    # -------------------------
    # BASIC DETAILS
    # -------------------------
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    activation_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=False)

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
    # BINARY TREE (FOR TREE DISPLAY & PAIR CALCULATION)
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
    # PLACEMENT TREE (OPTIONAL, IF YOU USE IT)
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
    joined_date = models.DateField(default=timezone.now)
    active = models.BooleanField(default=True)

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
    sponsor_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    flash_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    parent_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    stock_commission = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # -------------------------
    # BINARY ELIGIBILITY + CARRY FORWARD
    # -------------------------
    binary_eligible = models.BooleanField(default=False)
    binary_eligible_date = models.DateTimeField(null=True, blank=True)

    left_carry_forward = models.IntegerField(default=0)
    right_carry_forward = models.IntegerField(default=0)

    # DAILY JOIN TRACKING (for engine snapshot)
    left_joins_today = models.IntegerField(default=0)
    right_joins_today = models.IntegerField(default=0)

    # -------------------------
    # RANK / PACKAGE
    # -------------------------
    package = models.CharField(
        max_length=10,
        choices=[('Gold', 'Gold'), ('Silver', 'Silver'), ('Bronze', 'Bronze')],
        default='Bronze'
    )
    current_rank = models.CharField(max_length=50, null=True, blank=True)
    rank_assigned_at = models.DateTimeField(null=True, blank=True)

    # -------------------------
    # REPURCHASE BV SNAPSHOTS
    # -------------------------
    total_left_bv = models.BigIntegerField(default=0)
    total_right_bv = models.BigIntegerField(default=0)
    bv = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    rank_reward = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # -------------------------
    # STOCK POINT LEVEL
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

    def __str__(self):
        return f"{self.auto_id} - {self.name}"

    # ==========================================================
    # AUTO ID GENERATOR (SAFE SEQUENCE with RockCounter)
    # ==========================================================
    def save(self, *args, **kwargs):
        from django.db import transaction

        # =========================
        # AUTO ID GENERATOR (RockCounter)
        # =========================
        if not self.auto_id:
            with transaction.atomic():
                self.auto_id = generate_auto_id()  # ✅ use new safe generator from auto_id.py

        # =========================
        # AUTO MEMBER_ID (secondary)
        # =========================
        if not self.member_id:
            if self.id:
                self.member_id = f"rocky{self.id:03d}"
            else:
                self.member_id = "rockyTEMP"  # temporary
        super().save(*args, **kwargs)

        # Fix TEMP member_id after first save
        if self.member_id == "rockyTEMP":
            self.member_id = f"rocky{self.id:03d}"
            super().save(update_fields=["member_id"])

        # =========================
        # AUTO PLACEMENT = PARENT
        # =========================
        if self.parent and not self.placement:
            self.placement = self.parent

        # =========================
        # AUTO SPONSOR = PARENT
        # =========================
        if self.parent and not self.sponsor:
            self.sponsor = self.parent

        # =========================
        # AUTO SIDE ASSIGNMENT (left/right)
        # =========================
        if self.parent and not self.side:
            children_count = Member.objects.filter(parent=self.parent).exclude(id=self.id).count()
            if children_count == 0:
                self.side = "left"
            elif children_count == 1:
                self.side = "right"
            else:
                self.side = None  # extra child, manual adjustment

        # =========================
        # FINAL SAVE AFTER AUTO FIELDS
        # =========================
        super().save(update_fields=["placement", "sponsor", "side"])

    # ==========================================================
    # HELPER METHODS (TREE SAFE)
    # ==========================================================
    def left_child(self):
        return Member.objects.filter(parent=self, side='left').first()

    def right_child(self):
        return Member.objects.filter(parent=self, side='right').first()

    def has_pair(self):
        return bool(self.left_child() and self.right_child())

    # ==========================================================
    # REPURCHASE BV HELPERS
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
        total_bv = sum((o.product.bv_value * o.quantity) for o in repurchase_orders) if repurchase_orders else Decimal('0.00')
        return Decimal(total_bv)

    def calculate_bv(self):
        visited = set()
        queue = deque([self])
        left_bv = Decimal('0.00')
        right_bv = Decimal('0.00')

        rep_orders_self = Order.objects.filter(member=self, status="Paid")
        self_bv = sum((o.product.bv_value * o.quantity) for o in rep_orders_self) if rep_orders_self else Decimal('0.00')

        while queue:
            member = queue.popleft()
            if not member or member.id in visited:
                continue
            visited.add(member.id)

            if member != self:
                rep_orders = Order.objects.filter(member=member, status="Paid")
                member_bv = sum((o.product.bv_value * o.quantity) for o in rep_orders) if rep_orders else Decimal('0.00')
                if member.side == 'left':
                    left_bv += Decimal(member_bv)
                elif member.side == 'right':
                    right_bv += Decimal(member_bv)

            lc = member.left_child()
            rc = member.right_child()
            if lc:
                queue.append(lc)
            if rc:
                queue.append(rc)

        total_bv = Decimal(self_bv) + left_bv + right_bv
        return {
            "self_bv": Decimal(self_bv),
            "left_bv": left_bv,
            "right_bv": right_bv,
            "total_bv": total_bv,
            "matched_bv": min(left_bv, right_bv),
        }

    def get_bv_counts(self):
        def resolve_bv(root_member):
            if not root_member:
                return Decimal('0.00')
            data = root_member.calculate_bv()
            return Decimal(data.get("self_bv", Decimal('0.00'))) + Decimal(data.get("left_bv", Decimal('0.00'))) + Decimal(data.get("right_bv", Decimal('0.00')))
        left_bv = resolve_bv(self.left_child())
        right_bv = resolve_bv(self.right_child())
        return (left_bv, right_bv)

    def calculate_rank(self):
        from herbalapp.mlm_engine_binary import determine_rank_from_bv  # if you have it
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
        self.save(update_fields=["current_rank", "salary", "rank_reward", "rank_assigned_at"])

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
        return f"{self.member.auto_id} - {self.status} - {self.amount}"


# ==========================================================
# INCOME MODEL (Daily consolidated per member)
# ==========================================================
class Income(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)

    # 🔹 New field added
    binary_pairs = models.IntegerField(default=0)

    binary_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sponsor_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    flash_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    salary_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = ("member", "date")

    def __str__(self):
        return f"Income for {self.member.auto_id} on {self.date}"


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
        return f"{self.member.auto_id} - {self.commission_type} - {self.commission_amount}"


# ==========================================================
# RECORD MODELS (Audit logs)
# ==========================================================
class IncomeRecord(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.auto_id} - {self.type} - {self.amount}"


class CommissionRecord(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="earned_commissions")
    source_member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, related_name="generated_commissions")
    level = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


class BonusRecord(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    type = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.auto_id} - {self.type}"
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
# ORDER MODEL
# ==========================================================
class Order(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[("Paid", "Paid"), ("Pending", "Pending"), ("Cancelled", "Cancelled")],
        default="Pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.product and self.quantity:
            self.total_amount = self.product.mrp * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} - {self.member.auto_id}"


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
        if not self.active or self.months_paid >= self.duration_months:
            self.active = False
            self.save(update_fields=["active"])
            return False

        self.member.main_wallet = getattr(self.member, "main_wallet", Decimal('0.00')) + Decimal(self.monthly_income)
        self.member.save(update_fields=["main_wallet"])

        RankPayoutLog.objects.create(
            member=self.member,
            rank_reward=self,
            amount=self.monthly_income,
            paid_on=timezone.now().date()
        )

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
# DAILY INCOME REPORT (ENGINE SNAPSHOT)
# ==========================================================
class DailyIncomeReport(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    date = models.DateField()
    left_cf = models.IntegerField(default=0)
    right_cf = models.IntegerField(default=0)
    binary_eligible = models.BooleanField(default=False)
    eligibility_income = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    flash_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)

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

    # Eligibility (if you want to show it separately)
    binary_eligibility_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    # Total income
    total_income = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    # Optional flags
    sponsor_processed = models.BooleanField(default=False)
    wallet_income = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = ('member', 'date')
        ordering = ['-date', 'member']

    def __str__(self):
        return f"Daily Report for {self.member.auto_id} on {self.date}"

