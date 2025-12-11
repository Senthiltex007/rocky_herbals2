# herbalapp/models.py
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from collections import deque


def generate_auto_id():
    from herbalapp.models import Member
    last = Member.objects.order_by('-id').first()
    if not last:
        return "rocky001"
    last_id = last.auto_id.replace("rocky", "")
    new_number = int(last_id) + 1
    return f"rocky{new_number:03d}"

# ==========================================================
# AUTO COUNTER FOR ROCKY IDs
# ==========================================================
class RockCounter(models.Model):
    name = models.CharField(max_length=50, unique=True)
    last = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name}:{self.last}"

# ==========================================================
# MEMBER MODEL (MAIN Genealogy TREE)
# ==========================================================

class Member(models.Model):
    # Basic details
    member_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    auto_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    activation_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=False)

    # Identification / address
    aadhar = models.CharField(max_length=20, blank=True, null=True)
    aadhar_number = models.CharField(max_length=20, null=True, blank=True)
    place = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, null=True, blank=True)
    taluk = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.CharField(max_length=10, null=True, blank=True)

    # Parent & binary side
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')
    side = models.CharField(max_length=5, choices=[('left', 'Left'), ('right', 'Right')], null=True, blank=True)

    # Placement (NEW FIELD)
    placement = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='placement_downline'
    )

    # Binary pointers
    left_child = models.OneToOneField('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='left_of')
    right_child = models.OneToOneField('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='right_of')

    # Sponsor (referrer)
    sponsor = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='sponsored_members')

    # Package / rank
    package = models.CharField(max_length=10, choices=[('Gold', 'Gold'), ('Silver', 'Silver'), ('Bronze', 'Bronze')], default='Bronze')
    current_rank = models.CharField(max_length=50, null=True, blank=True)
    rank_assigned_at = models.DateTimeField(null=True, blank=True)

    # Account fields
    joined_date = models.DateField(default=timezone.now)
    active = models.BooleanField(default=True)

    # BV / rank reward fields
    bv = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    rank_reward = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Wallets
    main_wallet = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    repurchase_wallet = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    flash_wallet = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    # Income / counters
    binary_pairs = models.IntegerField(default=0)
    binary_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    parent_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    sponsor_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Flash bonus
    flash_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    # Stock commission
    stock_commission = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    # Salary income (persist per member)
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Eligibility + carry-forward
    binary_eligible = models.BooleanField(default=False)
    binary_eligible_date = models.DateTimeField(null=True, blank=True)

    left_cf = models.IntegerField(default=0)
    right_cf = models.IntegerField(default=0)

    left_join_count = models.IntegerField(default=0)
    right_join_count = models.IntegerField(default=0)

    left_new_today = models.IntegerField(default=0)
    right_new_today = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.auto_id or self.member_id or self.id} - {self.name}"
    # ==========================================================
    # ADD INSIDE Member MODEL (if not added earlier)
    # ==========================================================
    # under other member fields inside class Member(models.Model):

    position = models.CharField(
        max_length=10,
        choices=[('left', 'Left'), ('right', 'Right')],
        null=True, blank=True
    )

    # ==========================================================
    # LAST MONTH BV HELPER
    # ==========================================================
    def last_month_bv(self):
        from django.utils import timezone
        from datetime import timedelta
        today = timezone.now()
        first_day_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_day_last_month = today.replace(day=1) - timedelta(days=1)

        repurchase_orders = Order.objects.filter(
            member=self, 
            status="Paid",
            created_at__date__gte=first_day_last_month,
            created_at__date__lte=last_day_last_month
        )
        total_bv = sum([o.product.bv_value * o.quantity for o in repurchase_orders]) if repurchase_orders else Decimal('0.00')
        return total_bv

    # ==========================================================
    # AUTO ID GENERATOR (SAFE SEQUENCE)
    # ==========================================================
    def save(self, *args, **kwargs):
        # ===============================
        # MEMBER_ID (RockCounter safe)
        # ===============================
        if not self.member_id:
            with transaction.atomic():
                counter, created = RockCounter.objects.select_for_update().get_or_create(name='member')
                counter.last += 1
                next_member_num = counter.last
                self.member_id = f"rocky{next_member_num:03d}"  # rocky001, rocky002...
                counter.save()

        # ===============================
        # AUTO_ID (RockCounter safe)
        # ===============================
        if not self.auto_id:
            with transaction.atomic():
                counter, created = RockCounter.objects.select_for_update().get_or_create(name='auto_id')
                counter.last += 1
                next_auto_num = counter.last
                self.auto_id = f"rocky{next_auto_num:03d}"  # rocky001, rocky002...
                counter.save()

        super().save(*args, **kwargs)

    # ==========================================================
    # HELPERS
    # ==========================================================
    def has_left(self):
        return self.left_child is not None

    def has_right(self):
        return self.right_child is not None

    # ==========================================================
    # PYRAMID TREE (JSON)
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
                "children": [build(member.left_child), build(member.right_child)]
            }
        return build(self)

    # ==========================================================
    # BV CALCULATION - RESTRICTED TO REPURCHASE PRODUCTS ONLY
    # Uses BFS to avoid deep recursion and tracks visited nodes
    # ==========================================================
    def calculate_bv(self):
        visited = set()
        queue = deque([self])

        left_bv = Decimal('0.00')
        right_bv = Decimal('0.00')

        # Self BV (repurchase only)
        repurchase_orders = Order.objects.filter(member=self, status="Paid")
        self_bv = sum([o.product.bv_value * o.quantity for o in repurchase_orders]) if repurchase_orders else Decimal('0.00')

        while queue:
            member = queue.popleft()

            if not member:
                continue
            if member.id in visited:
                continue
            visited.add(member.id)

            # Skip the root member (self) for left/right aggregation
            if member != self:
                rep_orders = Order.objects.filter(member=member, status="Paid")
                bv_value = sum([o.product.bv_value * o.quantity for o in rep_orders]) if rep_orders else Decimal('0.00')

                if member.side == 'left':
                    left_bv += Decimal(bv_value)
                elif member.side == 'right':
                    right_bv += Decimal(bv_value)

            # Traverse children
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
            "matched_bv": min(left_bv, right_bv)
        }

    # ==========================================================
    # COUNT NEW MEMBERS TODAY UNDER SPONSOR
    # ==========================================================
    def get_new_members_today_count(self):
        today = timezone.now().date()
        return Member.objects.filter(sponsor=self, joined_date=today).count()

    # ==========================================================
    # BV COUNTS FOR LEFT / RIGHT (returns repurchase BV numbers)
    # ==========================================================
    def get_bv_counts(self):
        def resolve_bv(member):
            if not member:
                return Decimal('0.00')
            return Decimal(member.calculate_bv().get("self_bv", 0))
        left_bv = resolve_bv(self.left_child)
        right_bv = resolve_bv(self.right_child)
        return (left_bv, right_bv)

    # ==========================================================
    # COMMISSION TOTAL (sum grouped commission records)
    # ==========================================================
    def get_commission_total(self):
        district_commission = CommissionRecord.objects.filter(member=self, level="district").aggregate(Sum('amount'))["amount__sum"] or Decimal('0.00')
        taluk_commission = CommissionRecord.objects.filter(member=self, level="taluk").aggregate(Sum('amount'))["amount__sum"] or Decimal('0.00')
        pincode_commission = CommissionRecord.objects.filter(member=self, level="pincode").aggregate(Sum('amount'))["amount__sum"] or Decimal('0.00')
        return Decimal(district_commission) + Decimal(taluk_commission) + Decimal(pincode_commission)

    # ==========================================================
    # FULL INCOME CALCULATION
    # NOTE: this is a convenience function — you can adapt as needed.
    # ==========================================================
    def calculate_full_income(self):
        # New member join based binary calculations (daily)
        new_members_today = self.get_new_members_today_count()
        total_pairs = new_members_today // 2

        # Binary Income - daily cap 5 pairs
        binary_pairs = min(total_pairs, 5)
        # Each pair = ₹500
        binary_income_today = Decimal(binary_pairs) * Decimal('500.00')

        # Flash Bonus (example logic)
        remaining_pairs = max(total_pairs - binary_pairs, 0)
        flash_units = min(remaining_pairs // 5, 9)
        flash_bonus = Decimal(flash_units) * Decimal('1000.00')

        # Wash Out (example)
        wash_out_pairs = max(remaining_pairs - (flash_units * 5), 0)
        wash_out_members = wash_out_pairs * 2 + (new_members_today % 2)

        # Sponsor Income (sum of directs' binary income as per model description)
        directs = Member.objects.filter(sponsor=self)
        sponsor_income = sum([d.calculate_full_income().get("binary_income", Decimal('0.00')) for d in directs]) if directs else Decimal('0.00')

        # Salary slabs based on matched BV
        salary = Decimal('0.00')
        left_bv, right_bv = self.get_bv_counts()
        matched_bv = min(left_bv, right_bv)
        if matched_bv >= Decimal('250000'):
            salary = Decimal('10000.00')
        elif matched_bv >= Decimal('100000'):
            salary = Decimal('5000.00')
        elif matched_bv >= Decimal('50000'):
            salary = Decimal('3000.00')

        # Stock Commission
        total_stock_commission = self.get_commission_total()

        # Repurchase Wallet (example: equals flash bonus)
        repurchase_wallet_amount = flash_bonus

        # Total Income (exclude joining fee)
        total_income_all = Decimal(binary_income_today) + Decimal(sponsor_income) + Decimal(salary) + Decimal(total_stock_commission)

        return {
            "joining": Decimal('3000.00'),
            "binary_income": Decimal(binary_income_today),
            "flash_bonus": Decimal(flash_bonus),
            "sponsor_income": Decimal(sponsor_income),
            "salary": Decimal(salary),
            "stock_commission": Decimal(total_stock_commission),
            "repurchase_wallet": Decimal(repurchase_wallet_amount),
            "wash_out_members": wash_out_members,
            "total_income_all": Decimal(total_income_all)
        }

    # ==========================================================
    # WRAPPER ENGINE (calls calculate_full_income and updates DB)
    # ==========================================================
    def run_income_engine(self):
        data = self.calculate_full_income()

        # Update DB fields
        self.binary_income += data["binary_income"]
        self.sponsor_income += data["sponsor_income"]
        self.flash_bonus += data["flash_bonus"]
        self.repurchase_wallet += data["repurchase_wallet"]
        self.rank_reward += data.get("rank_reward", Decimal("0.00"))
        self.stock_commission += data["stock_commission"]
        self.salary += data["salary"]   # ✅ New line
        self.save()

        # Log into DailyIncomeReport
        DailyIncomeReport.objects.create(
            member=self,
            binary_income=data["binary_income"],
            flash_bonus=data["flash_bonus"],
            sponsor_income=data["sponsor_income"],
            salary=data["salary"],
            stock_commission=data["stock_commission"],
            total_income=data["total_income_all"]
        )

        return data


# ==========================================================
# PAYMENT MODEL
# ==========================================================
class Payment(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=[('Paid', 'Paid'), ('Unpaid', 'Unpaid')])
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.name} - {self.status} - {self.amount}"


# ==========================================================
# INCOME MODEL
# ==========================================================
class Income(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)

    joining_package = models.IntegerField(default=3000)
    binary_pairs = models.IntegerField(default=0)
    binary_income = models.IntegerField(default=0)
    sponsor_income = models.IntegerField(default=0)
    flash_out_bonus = models.IntegerField(default=0)
    salary_income = models.IntegerField(default=0)

    def __str__(self):
        return f"Income for {self.member.name} on {self.date}"


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
# DAILY INCOME REPORT TABLE
# ==========================================================
class DailyIncomeReport(models.Model):
    date = models.DateField(auto_now_add=True)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)

    binary_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    flash_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    sponsor_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))   # ✅ keep salary log
    stock_commission = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    total_income = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.member.name} - {self.date}"

