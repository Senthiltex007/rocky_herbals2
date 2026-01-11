# herbalapp/engine/run.py

from datetime import date
from decimal import Decimal
from django.db import transaction

from herbalapp.models import Member, DailyIncomeReport, CommissionRecord

# -------------------------
# CONSTANTS
# -------------------------
PAIR_VALUE = Decimal("500")
ELIGIBILITY_BONUS = Decimal("500")
DAILY_BINARY_PAIR_LIMIT = 5
FLASHOUT_PAIR_UNIT = 5
FLASHOUT_UNIT_VALUE = Decimal("1000")
MAX_FLASHOUT_UNITS = 9


# =====================================================
# 🔁 TREE HELPERS (MATCH YOUR MODEL)
# =====================================================
def get_left_children(member):
    return Member.objects.filter(parent=member, side="left")

def get_right_children(member):
    return Member.objects.filter(parent=member, side="right")


# =====================================================
# 💰 SPONSOR INCOME
# =====================================================
def process_sponsor_income(child, run_date, binary_income, eligibility_income):
    sponsor_amount = binary_income + eligibility_income
    if sponsor_amount <= 0:
        return

    sponsor_receiver = child.sponsor
    if not sponsor_receiver:
        return

    # sponsor must have at least one pair in lifetime
    if sponsor_receiver.lifetime_pairs < 1:
        return

    CommissionRecord.objects.get_or_create(
        member=sponsor_receiver,
        source_member=child,
        date=run_date,
        defaults={
            "amount": sponsor_amount,
            "income_type": "SPONSOR"
        }
    )


# =====================================================
# ⚙️ MEMBER DAILY ENGINE
# =====================================================
@transaction.atomic
def calculate_member_income_for_day(member, run_date):

    if DailyIncomeReport.objects.filter(member=member, date=run_date).exists():
        return

    # -------------------------
    # TODAY JOINS
    # -------------------------
    left_today = get_left_children(member).filter(created_at__date=run_date).count()
    right_today = get_right_children(member).filter(created_at__date=run_date).count()

    L = member.total_left_bv + left_today
    R = member.total_right_bv + right_today

    binary_income = Decimal("0")
    eligibility_income = Decimal("0")
    flashout_income = Decimal("0")
    flashout_units = 0
    washed_pairs = 0
    binary_pairs_today = 0

    # -------------------------
    # ELIGIBILITY (1:1 minimum)
    # -------------------------
    if member.lifetime_pairs == 0:
        if L >= 1 and R >= 1:
            eligibility_income = ELIGIBILITY_BONUS
            member.update_lifetime_pairs(1)
            L -= 1
            R -= 1
        else:
            return

    # -------------------------
    # DAILY BINARY (MAX 5)
    # -------------------------
    available_pairs = min(L, R)
    binary_pairs_today = min(available_pairs, DAILY_BINARY_PAIR_LIMIT)
    binary_income = binary_pairs_today * PAIR_VALUE

    member.update_lifetime_pairs(binary_pairs_today)

    L -= binary_pairs_today
    R -= binary_pairs_today

    # -------------------------
    # FLASHOUT
    # -------------------------
    remaining_pairs = min(L, R)
    flashout_units = min(remaining_pairs // FLASHOUT_PAIR_UNIT, MAX_FLASHOUT_UNITS)
    flashout_income = flashout_units * FLASHOUT_UNIT_VALUE

    L -= flashout_units * FLASHOUT_PAIR_UNIT
    R -= flashout_units * FLASHOUT_PAIR_UNIT

    # -------------------------
    # WASHOUT
    # -------------------------
    washed_pairs = min(L, R)
    L -= washed_pairs
    R -= washed_pairs

    # -------------------------
    # SAVE BV
    # -------------------------
    member.total_left_bv = L
    member.total_right_bv = R
    member.save(update_fields=["total_left_bv", "total_right_bv"])

    # -------------------------
    # DAILY REPORT
    # -------------------------
    DailyIncomeReport.objects.create(
        member=member,
        date=run_date,
        left_joins=left_today,
        right_joins=right_today,
        binary_pairs_paid=binary_pairs_today,
        binary_income=binary_income,
        flashout_units=flashout_units,
        flashout_wallet_income=flashout_income,
        washed_pairs=washed_pairs,
        sponsor_income=Decimal("0.00"),
        total_income=binary_income + flashout_income + eligibility_income
    )

    # -------------------------
    # SPONSOR INCOME
    # -------------------------
    process_sponsor_income(
        child=member,
        run_date=run_date,
        binary_income=binary_income,
        eligibility_income=eligibility_income
    )


# =====================================================
# 🌳 ROOT → DOWNLINE ENGINE
# =====================================================
def process_member_daily(root_member, run_date=None):
    if not run_date:
        run_date = date.today()

    def dfs(member):
        calculate_member_income_for_day(member, run_date)
        for child in Member.objects.filter(parent=member):
            dfs(child)

    dfs(root_member)

