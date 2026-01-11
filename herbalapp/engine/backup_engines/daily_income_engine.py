# herbalapp/engine/daily_income_engine.py
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport, CommissionRecord

PAIR_VALUE = Decimal("500")
ELIGIBILITY_BONUS = Decimal("500")
DAILY_BINARY_PAIR_LIMIT = 5
FLASHOUT_PAIR_UNIT = 5
FLASHOUT_UNIT_VALUE = Decimal("1000")
MAX_FLASHOUT_UNITS = 9

# Sponsor income rules
def process_sponsor_income(child: Member, run_date, binary_income: Decimal, eligibility_income: Decimal):
    sponsor_amount = binary_income + eligibility_income
    if sponsor_amount <= 0:
        return

    sponsor_receiver = None
    if child.sponsor and child.placement:
        if child.sponsor == child.placement:
            sponsor_receiver = child.placement.parent
        else:
            sponsor_receiver = child.sponsor

    if not sponsor_receiver:
        return

    if not getattr(sponsor_receiver, "sponsor_eligible", False):
        return

    CommissionRecord.objects.get_or_create(
        member=sponsor_receiver,
        source_member=child,
        date=run_date,
        defaults={"amount": sponsor_amount, "income_type": "SPONSOR"}
    )

@transaction.atomic
def calculate_member_income_for_day(member: Member, run_date=None):
    if run_date is None:
        run_date = timezone.now().date()

    if DailyIncomeReport.objects.filter(member=member, date=run_date).exists():
        return  # Already processed

    # Fetch joins & carry-forward
    left_today = member.left_joins_today
    right_today = member.right_joins_today
    L = member.left_carry_forward + left_today
    R = member.right_carry_forward + right_today

    eligibility_income = Decimal("0")
    binary_income = Decimal("0")
    flashout_units = 0
    flashout_income = Decimal("0")
    washed_pairs = 0
    became_eligible_today = False

    # ---------------- BINARY ELIGIBILITY ----------------
    if not member.binary_eligible:
        if (L >= 1 and R >= 2) or (L >= 2 and R >= 1):
            member.binary_eligible = True
            eligibility_income = ELIGIBILITY_BONUS
            became_eligible_today = True
            if L >= 1 and R >= 2:
                L -= 1
                R -= 2
            else:
                L -= 2
                R -= 1
        else:
            washed_pairs = min(L, R)
            L -= washed_pairs
            R -= washed_pairs
            member.left_carry_forward = L
            member.right_carry_forward = R
            member.save(update_fields=["left_carry_forward", "right_carry_forward"])
            return

    # ---------------- DAILY BINARY INCOME ----------------
    available_pairs = min(L, R)
    already_used = 1 if became_eligible_today else 0
    remaining_cap = max(DAILY_BINARY_PAIR_LIMIT - already_used, 0)
    binary_pairs_today = min(available_pairs, remaining_cap)
    binary_income = binary_pairs_today * PAIR_VALUE
    L -= binary_pairs_today
    R -= binary_pairs_today

    # ---------------- FLASHOUT ----------------
    remaining_pairs = min(L, R)
    flashout_units = min(remaining_pairs // FLASHOUT_PAIR_UNIT, MAX_FLASHOUT_UNITS)
    flashout_income = flashout_units * FLASHOUT_UNIT_VALUE
    L -= flashout_units * FLASHOUT_PAIR_UNIT
    R -= flashout_units * FLASHOUT_PAIR_UNIT

    # ---------------- WASHOUT ----------------
    washed_pairs = min(L, R)
    L -= washed_pairs
    R -= washed_pairs

    # ---------------- SAVE ----------------
    member.left_carry_forward = L
    member.right_carry_forward = R
    member.save(update_fields=["left_carry_forward", "right_carry_forward", "binary_eligible"])

    DailyIncomeReport.objects.create(
        member=member,
        date=run_date,
        left_joins=left_today,
        right_joins=right_today,
        left_cf_before=member.left_carry_forward,
        right_cf_before=member.right_carry_forward,
        left_cf_after=L,
        right_cf_after=R,
        binary_pairs_paid=binary_pairs_today,
        binary_income=binary_income,
        flashout_units=flashout_units,
        flashout_wallet_income=flashout_income,
        washed_pairs=washed_pairs,
        total_left_bv=member.total_left_bv,
        total_right_bv=member.total_right_bv,
        salary_income=Decimal("0.00"),
        rank_title=member.current_rank or "",
        sponsor_income=Decimal("0.00"),
        total_income=binary_income + flashout_income + eligibility_income,
    )

    process_sponsor_income(member, run_date, binary_income, eligibility_income)

