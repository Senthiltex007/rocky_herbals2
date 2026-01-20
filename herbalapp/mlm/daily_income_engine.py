# ==========================================================
# herbalapp/mlm/daily_income_engine.py
# ==========================================================

from decimal import Decimal
from herbalapp.models import DailyIncomeReport


def calculate_daily_income(report: DailyIncomeReport):
    """
    Calculate and update TOTAL income for ONE DailyIncomeReport

    INCLUDED (ONLY ONCE):
    - Binary eligibility income
    - Binary income
    - Sponsor income
    - Flashout wallet income

    EXCLUDED (to avoid duplication):
    - eligibility_income (duplicate / legacy)
    - flash_bonus (old naming)
    - salary (handled separately if needed)
    """

    total = (
        (report.binary_eligibility_income or Decimal("0.00")) +
        (report.binary_income or Decimal("0.00")) +
        (report.sponsor_income or Decimal("0.00")) +
        (report.flashout_wallet_income or Decimal("0.00"))
    )

    report.total_income = total
    report.save(update_fields=["total_income"])

    return total

