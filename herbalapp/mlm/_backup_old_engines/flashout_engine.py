# ==========================================================
# herbalapp/mlm/flashout_engine.py
# ==========================================================

from decimal import Decimal
from django.db import transaction
from datetime import date

from herbalapp.models import Member, DailyIncomeReport

FLASHOUT_PAIR_UNIT = 5           # 5 pairs = 1 flashout unit
FLASHOUT_UNIT_VALUE = Decimal("1000")
MAX_FLASHOUT_UNITS = 9
ROOT_ID = "rocky004"

@transaction.atomic
def run_flashout_engine(run_date: date):
    """
    Flashout Bonus Engine (Updated with binary eligibility logic)

    Rules:
    - Binary income must be processed first
    - Count remaining pairs after today's binary income (washout pairs included)
    - 5 pairs = 1 flashout unit, max 9 units/day
    - Flashout bonus credited to main_wallet
    - Remaining unpaired pairs carried forward
    """

    members = Member.objects.exclude(auto_id=ROOT_ID).order_by("id")

    for member in members:
        try:
            report = DailyIncomeReport.objects.get(member=member, date=run_date)
        except DailyIncomeReport.DoesNotExist:
            continue

        # --------------------------------------------------
        # Total available pairs for the day
        # --------------------------------------------------
        total_left = member.left_joins_today + member.left_carry_forward
        total_right = member.right_joins_today + member.right_carry_forward
        total_pairs = min(total_left, total_right)

        # --------------------------------------------------
        # Subtract pairs already paid via binary income today
        # --------------------------------------------------
        binary_income = getattr(report, "binary_income", Decimal("0.00"))
        binary_pairs_paid = int(binary_income / 500)  # 500 per pair
        remaining_pairs = max(total_pairs - binary_pairs_paid, 0)

        if remaining_pairs <= 0:
            continue

        # --------------------------------------------------
        # Calculate flashout units
        # --------------------------------------------------
        flashout_units_today = min(remaining_pairs // FLASHOUT_PAIR_UNIT, MAX_FLASHOUT_UNITS)
        flashout_income = flashout_units_today * FLASHOUT_UNIT_VALUE

        if flashout_income <= 0:
            continue

        # --------------------------------------------------
        # Deduct used pairs from carry forward
        # --------------------------------------------------
        used_pairs_for_flashout = flashout_units_today * FLASHOUT_PAIR_UNIT
        remaining_left = total_left - binary_pairs_paid - used_pairs_for_flashout
        remaining_right = total_right - binary_pairs_paid - used_pairs_for_flashout

        member.left_carry_forward = max(remaining_left, 0)
        member.right_carry_forward = max(remaining_right, 0)
        member.save(update_fields=["left_carry_forward", "right_carry_forward"])

        # --------------------------------------------------
        # Update report
        # --------------------------------------------------
        report.flashout_units = flashout_units_today
        report.flashout_wallet_income = flashout_income
        report.total_income += flashout_income
        report.save(update_fields=["flashout_units", "flashout_wallet_income", "total_income"])

        # --------------------------------------------------
        # Credit main wallet
        # --------------------------------------------------
        member.main_wallet += flashout_income
        member.save(update_fields=["main_wallet"])

