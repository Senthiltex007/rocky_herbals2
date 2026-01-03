# herbalapp/engines/binary_daily.py

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport

BINARY_PER_PAIR = Decimal("500.00")
MAX_BINARY_PAIRS_PER_DAY = 5
FLASHOUT_UNIT_PAIRS = 5
FLASHOUT_UNIT_VALUE = Decimal("1000.00")
MAX_FLASHOUT_UNITS_PER_DAY = 9

@transaction.atomic
def process_daily_binary(member: Member, fresh_pairs_today: int, run_date=None):
    """
    fresh_pairs_today: only new 1:1 pairs formed today (excluding locked/unlock pair).
    """
    if run_date is None:
        run_date = timezone.now().date()

    report, _ = DailyIncomeReport.objects.get_or_create(member=member, date=run_date, defaults={
        "eligibility_income": Decimal("0.00"),
        "binary_income": Decimal("0.00"),
        "sponsor_income": Decimal("0.00"),
        "wallet_income": Decimal("0.00"),
        "salary_income": Decimal("0.00"),
        "total_income": Decimal("0.00"),
    })

    # Binary income cap
    binary_pairs_paid = min(fresh_pairs_today, MAX_BINARY_PAIRS_PER_DAY)
    report.binary_pairs_paid = binary_pairs_paid
    report.binary_income = (report.binary_income or Decimal("0.00")) + (Decimal(binary_pairs_paid) * BINARY_PER_PAIR)

    # Flashout units
    remaining_pairs = max(fresh_pairs_today - binary_pairs_paid, 0)
    flash_units = min(remaining_pairs // FLASHOUT_UNIT_PAIRS, MAX_FLASHOUT_UNITS_PER_DAY)
    report.flashout_units = (report.flashout_units or 0) + flash_units
    report.wallet_income = (report.wallet_income or Decimal("0.00")) + (Decimal(flash_units) * FLASHOUT_UNIT_VALUE)

    # Washed pairs (beyond flashout cap or leftover < 5)
    washed_pairs = remaining_pairs - (flash_units * FLASHOUT_UNIT_PAIRS)
    report.washed_pairs = (report.washed_pairs or 0) + washed_pairs

    # Total recompute
    report.total_income = (
        (report.eligibility_income or Decimal("0.00")) +
        (report.binary_income or Decimal("0.00")) +
        (report.sponsor_income or Decimal("0.00")) +
        (report.wallet_income or Decimal("0.00")) +
        (report.salary_income or Decimal("0.00"))
    )
    report.save()

    return {
        "binary_pairs_paid": binary_pairs_paid,
        "flashout_units": flash_units,
        "washed_pairs": washed_pairs,
        "binary_income": str(report.binary_income),
        "wallet_income": str(report.wallet_income),
    }

