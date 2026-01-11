# herbalapp/management/commands/mlm_run_daily_income.py

from decimal import Decimal
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from herbalapp.models import Member, DailyIncomeReport

# --------------------------
# CONSTANTS
# --------------------------
PAIR_VALUE = Decimal("500")
ELIGIBILITY_BONUS = Decimal("500")
DAILY_BINARY_PAIR_LIMIT = 5

FLASHOUT_UNIT_PAIRS = 5
FLASHOUT_UNIT_VALUE = Decimal("1000")
MAX_FLASHOUT_UNITS_PER_DAY = 9


# --------------------------
# HELPER
# --------------------------
def get_sponsor_for_income(member: Member):
    """
    Rule 1 & 2:
    - If placement == sponsor → placement parent gets income
    - Else sponsor gets income
    """
    if not member.sponsor:
        return None

    if member.placement == member.sponsor:
        return member.placement.parent
    return member.sponsor


# --------------------------
# CORE LOGIC
# --------------------------
def process_member_daily_income(member: Member, run_date):
    # Skip if report already exists
    if DailyIncomeReport.objects.filter(member=member, date=run_date).exists():
        return

    left_today = member.left_joins_today or 0
    right_today = member.right_joins_today or 0

    L = (member.left_carry_forward or 0) + left_today
    R = (member.right_carry_forward or 0) + right_today

    binary_income = Decimal("0")
    eligibility_bonus = Decimal("0")
    flashout_income = Decimal("0")
    flashout_units = 0
    washed_pairs = 0
    became_eligible_today = False
    locked_pairs_used = 0

    # --------------------------
    # ELIGIBILITY CHECK
    # --------------------------
    if not member.binary_eligible:
        if (L >= 2 and R >= 1) or (L >= 1 and R >= 2):
            member.binary_eligible = True
            eligibility_bonus = ELIGIBILITY_BONUS
            became_eligible_today = True

            # LOCKED eligibility pair
            if L >= 2:
                L -= 2
                R -= 1
            else:
                L -= 1
                R -= 2
            locked_pairs_used = 1
        else:
            # save carry forward only
            member.left_carry_forward = L
            member.right_carry_forward = R
            member.save(update_fields=["left_carry_forward", "right_carry_forward"])
            return

    # --------------------------
    # DAILY BINARY INCOME
    # --------------------------
    available_pairs = min(L, R)
    remaining_cap = DAILY_BINARY_PAIR_LIMIT - locked_pairs_used

    binary_pairs_today = min(available_pairs, remaining_cap)
    binary_income = binary_pairs_today * PAIR_VALUE

    L -= binary_pairs_today
    R -= binary_pairs_today

    # --------------------------
    # FLASHOUT
    # --------------------------
    remaining_pairs = min(L, R)
    flashout_units = min(
        remaining_pairs // FLASHOUT_UNIT_PAIRS,
        MAX_FLASHOUT_UNITS_PER_DAY
    )

    flashout_pairs_used = flashout_units * FLASHOUT_UNIT_PAIRS
    flashout_income = flashout_units * FLASHOUT_UNIT_VALUE

    L -= flashout_pairs_used
    R -= flashout_pairs_used

    # --------------------------
    # WASHOUT
    # --------------------------
    washed_pairs = min(L, R)
    L -= washed_pairs
    R -= washed_pairs

    # --------------------------
    # SAVE CARRY FORWARD
    # --------------------------
    member.left_carry_forward = L
    member.right_carry_forward = R
    member.save(update_fields=["binary_eligible", "left_carry_forward", "right_carry_forward"])

    # --------------------------
    # SPONSOR INCOME
    # --------------------------
    sponsor_income = Decimal("0")
    sponsor = get_sponsor_for_income(member)
    if sponsor and sponsor.binary_eligible:
        sponsor_income = eligibility_bonus + binary_income
        sponsor.income += sponsor_income
        sponsor.save(update_fields=["income"])

    # --------------------------
    # SAVE DAILY REPORT
    # --------------------------
    DailyIncomeReport.objects.create(
        member=member,
        date=run_date,
        left_joins=left_today,
        right_joins=right_today,
        left_cf_before=L + left_today,
        right_cf_before=R + right_today,
        left_cf_after=L,
        right_cf_after=R,
        binary_pairs_paid=binary_pairs_today,
        binary_income=binary_income,
        flashout_units=flashout_units,
        flashout_wallet_income=flashout_income,
        washed_pairs=washed_pairs,
        salary_income=member.salary,
        rank_title=member.current_rank,
        sponsor_income=sponsor_income,
        total_income=binary_income + flashout_income + eligibility_bonus,
    )


# --------------------------
# MANAGEMENT COMMAND
# --------------------------
class Command(BaseCommand):
    help = "Run MLM daily income (supports custom date)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="YYYY-MM-DD (default: today)"
        )

    @transaction.atomic
    def handle(self, *args, **options):
        date_str = options.get("date")
        run_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_str else timezone.now().date()
        )

        members = Member.objects.all()
        print(f"✅ {members.count()} members found. Running income calculation...")

        for member in members:
            process_member_daily_income(member, run_date)

        self.stdout.write(self.style.SUCCESS("✅ MLM daily income completed"))

