# ==========================================================
# herbalapp/mlm/binary_engine.py
# ==========================================================

from datetime import date
from decimal import Decimal

from herbalapp.models import Member, DailyIncomeReport
from herbalapp.mlm.daily_income_engine import calculate_daily_income

PAIR_INCOME = Decimal("500.00")
MAX_PAIRS_PER_DAY = 5
FLASHOUT_PAIR_UNIT = 5
FLASHOUT_UNIT_INCOME = 1000
MAX_FLASHOUT_UNITS_PER_DAY = 9


def run_binary_engine(member: Member, run_date: date):
    """
    Binary Income Engine (DAILY)
    
    RULES IMPLEMENTED:
    ------------------
    1️⃣ Binary eligible = lifetime condition (1:2 or 2:1) → already handled earlier
    2️⃣ After eligible:
        - Every NEW 1:1 pair = ₹500
        - Max 5 pairs/day = ₹2500
    3️⃣ On eligibility day:
        - 1:2 or 2:1 counts as FIRST PAIR
        - That pair already paid as eligibility income (₹500)
        - DO NOT pay again as binary income
        - Only NEW 1:1 pairs count from 2nd pair onwards
    4️⃣ Unpaired members used in eligibility are LOCKED for life
    5️⃣ Extra pairs go to flashout wallet (5 pairs = 1 flashout unit, max 9 units/day)
    """

    if not member.binary_eligible:
        return

    report, _ = DailyIncomeReport.objects.get_or_create(
        member=member,
        date=run_date,
        defaults={
            "binary_income": Decimal("0.00"),
            "flashout_wallet_income": Decimal("0.00"),
        }
    )

    # -------------------------
    # Total left/right (today + carry forward)
    # -------------------------
    total_left = member.left_joins_today + member.left_carry_forward
    total_right = member.right_joins_today + member.right_carry_forward

    total_pairs = min(total_left, total_right)
    if total_pairs <= 0:
        return

    # -------------------------
    # Detect eligibility day
    # -------------------------
    eligibility_today = report.binary_eligibility_income > 0

    # -------------------------
    # Payable pairs calculation
    # -------------------------
    if eligibility_today:
        # 1st pair already paid via eligibility income
        payable_pairs = max(total_pairs - 1, 0)
    else:
        payable_pairs = total_pairs

    # Max 5 pairs/day
    daily_pairs = min(payable_pairs, MAX_PAIRS_PER_DAY)
    binary_income = daily_pairs * PAIR_INCOME

    # -------------------------
    # Extra pairs → flashout wallet
    # -------------------------
    extra_pairs = max(total_pairs - daily_pairs - (1 if eligibility_today else 0), 0)
    flashout_units = min(extra_pairs // FLASHOUT_PAIR_UNIT, MAX_FLASHOUT_UNITS_PER_DAY)
    flashout_income = flashout_units * FLASHOUT_UNIT_INCOME

    # -------------------------
    # Save daily report
    # -------------------------
    report.binary_income += binary_income
    report.flashout_wallet_income += flashout_income
    calculate_daily_income(report)

    # -------------------------
    # Update member wallet
    # -------------------------
    member.main_wallet += binary_income
    member.save(update_fields=["main_wallet"])

