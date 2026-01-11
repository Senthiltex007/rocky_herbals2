# ==========================================================
# herbalapp/management/commands/mlm_run_daily.py
# ==========================================================
from decimal import Decimal
from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction
from herbalapp.models import Member, DailyIncomeReport

# -------------------------
# CONSTANTS
# -------------------------
PAIR_VALUE = Decimal("500")
ELIGIBILITY_BONUS = Decimal("500")
DAILY_BINARY_PAIR_LIMIT = 5
FLASHOUT_PAIR_UNIT = 5
FLASHOUT_UNIT_VALUE = Decimal("1000")
MAX_FLASHOUT_UNITS = 9
ROOT_ID = "rocky004"

# -------------------------
# SPONSOR INCOME ENGINE (FINAL RULES)
# -------------------------
def process_sponsor_income(child: Member, run_date, eligibility_income: Decimal, sponsor_income_today: Decimal):
    """
    Sponsor income rules:
    1. If placement_id == sponsor_id → income goes to placement's parent
    2. If placement_id != sponsor_id → income goes to sponsor_id
    3. Receiver must already be binary eligible (1:1 pair complete)
    4. Amount = child eligibility bonus (500) + child sponsor income that day
    """

    sponsor_receiver = None

    # Rule 1 & 2: decide who gets sponsor income
    if child.placement_id and child.sponsor_id:
        if child.placement_id == child.sponsor_id:
            # Placement and sponsor same → income goes to placement's parent
            sponsor_receiver = child.placement.parent if child.placement else None
        else:
            # Different → income goes to sponsor directly
            sponsor_receiver = child.sponsor

    if not sponsor_receiver:
        return

    # Rule 3: must be binary eligible
    if not sponsor_receiver.binary_eligible:
        return

    # Rule 4: calculate sponsor amount
    sponsor_amount = eligibility_income + sponsor_income_today
    if sponsor_amount <= 0:
        return

    # Credit sponsor wallet
    sponsor_receiver.main_wallet += sponsor_amount
    sponsor_receiver.save(update_fields=["main_wallet"])

    # Update / create daily report
    report, created = DailyIncomeReport.objects.get_or_create(
        member=sponsor_receiver,
        date=run_date,
        defaults={
            "sponsor_income": sponsor_amount,
            "total_income": sponsor_amount,
        }
    )
    if not created:
        report.sponsor_income += sponsor_amount
        report.total_income += sponsor_amount
        report.save(update_fields=["sponsor_income", "total_income"])

# -------------------------
# DAILY INCOME CALCULATION
# -------------------------
@transaction.atomic
def calculate_member_income_for_day(member: Member, run_date: date):
    """Full MLM logic per member for the day"""
    if member.auto_id == ROOT_ID:
        return  # Skip dummy/root member

    # Avoid duplicate reports
    if DailyIncomeReport.objects.filter(member=member, date=run_date).exists():
        return

    left_today = member.left_joins_today or 0
    right_today = member.right_joins_today or 0

    L = (member.left_carry_forward or 0) + left_today
    R = (member.right_carry_forward or 0) + right_today

    eligibility_income = Decimal("0")
    binary_income = Decimal("0")
    flashout_units = 0
    flashout_income = Decimal("0")
    washed_pairs = 0
    became_eligible_today = False

    # -------------------------
    # BINARY ELIGIBILITY (1:2 or 2:1)
    # -------------------------
    if not member.binary_eligible:
        if (L >= 2 and R >= 1) or (L >= 1 and R >= 2):
            member.binary_eligible = True
            eligibility_income = ELIGIBILITY_BONUS
            became_eligible_today = True
            # Lock first pair for eligibility
            if L >= 2:
                L -= 2
                R -= 1
            else:
                L -= 1
                R -= 2
        else:
            # Carry forward unpaired
            washed_pairs = min(L, R)
            L -= washed_pairs
            R -= washed_pairs
            member.left_carry_forward = L
            member.right_carry_forward = R
            member.save(update_fields=["left_carry_forward", "right_carry_forward"])
            return

    # -------------------------
    # DAILY BINARY INCOME (max 5 pairs/day)
    # -------------------------
    available_pairs = min(L, R)
    used_pairs_today = 1 if became_eligible_today else 0  # eligibility pair counted
    remaining_cap = max(DAILY_BINARY_PAIR_LIMIT - used_pairs_today, 0)
    binary_pairs_today = min(available_pairs, remaining_cap)
    binary_income = binary_pairs_today * PAIR_VALUE
    L -= binary_pairs_today
    R -= binary_pairs_today

    # -------------------------
    # FLASHOUT BONUS (repurchase wallet only)
    # -------------------------
    remaining_pairs = min(L, R)
    flashout_units = min(remaining_pairs // FLASHOUT_PAIR_UNIT, MAX_FLASHOUT_UNITS)
    flashout_income = flashout_units * FLASHOUT_UNIT_VALUE
    L -= flashout_units * FLASHOUT_PAIR_UNIT
    R -= flashout_units * FLASHOUT_PAIR_UNIT

    # -------------------------
    # WASHOUT (no income)
    # -------------------------
    washed_pairs = min(L, R)
    L -= washed_pairs
    R -= washed_pairs

    # -------------------------
    # SAVE CARRY FORWARD
    # -------------------------
    member.left_carry_forward = L
    member.right_carry_forward = R
    member.binary_eligible = member.binary_eligible
    member.save(update_fields=["left_carry_forward", "right_carry_forward", "binary_eligible"])

    # -------------------------
    # SAVE DAILY INCOME REPORT
    # -------------------------
    report, created = DailyIncomeReport.objects.get_or_create(
        member=member,
        date=run_date,
        defaults={
            "left_joins": left_today,
            "right_joins": right_today,
            "left_cf_before": L + left_today,
            "right_cf_before": R + right_today,
            "left_cf_after": L,
            "right_cf_after": R,
            "binary_pairs_paid": binary_pairs_today,
            "binary_income": binary_income,
            "flashout_units": flashout_units,
            "flashout_wallet_income": flashout_income,
            "washed_pairs": washed_pairs,
            "total_left_bv": member.total_left_bv,
            "total_right_bv": member.total_right_bv,
            "salary_income": member.salary or Decimal("0.00"),
            "rank_title": member.current_rank or "",
            "sponsor_income": Decimal("0.00"),
            "total_income": binary_income + flashout_income + eligibility_income,
        }
    )

    # -------------------------
    # SPONSOR INCOME
    # -------------------------
    # Child eligibility bonus (500) + child’s own sponsor income that day
    child_report = DailyIncomeReport.objects.filter(member=member, date=run_date).first()
    child_sponsor_income_today = child_report.sponsor_income if child_report else Decimal("0.00")

    process_sponsor_income(
        child=member,
        run_date=run_date,
        eligibility_income=eligibility_income,
        sponsor_income_today=child_sponsor_income_today,
    )

# -------------------------
# MANAGEMENT COMMAND
# -------------------------
class Command(BaseCommand):
    help = "Run daily MLM engine (binary + sponsor + flashout + eligibility) for all members"

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='Run engine for a specific date (YYYY-MM-DD)')

    def handle(self, *args, **options):
        date_str = options.get('date')
        if date_str:
            try:
                target_date = date.fromisoformat(date_str)
            except ValueError:
                self.stdout.write(self.style.ERROR(f"❌ Invalid date format: {date_str}. Use YYYY-MM-DD"))
                return
        else:
            target_date = date.today()

        self.stdout.write(f"🚀 Daily engine run start: {target_date}")

        # -------------------------
        # PROCESS ALL MEMBERS IN ORDER
        # Ensure children processed before parents
        # -------------------------
        all_members = Member.objects.all().order_by('id')
        for member in all_members:
            try:
                calculate_member_income_for_day(member, target_date)
                self.stdout.write(f"✅ Engine run for {member.auto_id}")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️ Engine fail {member.auto_id}: {str(e)}"))

        self.stdout.write("🎯 Daily engine + audit completed successfully.")

