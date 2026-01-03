# herbalapp/engines/binary_unlock.py

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport

ELIGIBILITY_BONUS = Decimal("500.00")
BINARY_PER_PAIR = Decimal("500.00")
MAX_BINARY_PAIRS_PER_DAY = 5

@transaction.atomic
def process_unlock_day(member: Member, run_date=None):
    """
    When member reaches 1:2 or 2:1:
    - Pay eligibility bonus ₹500 once.
    - Lock the extra unpaired member on heavy side (mark as locked).
    - Do NOT count the unlock pair for binary income.
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

    # Pay eligibility once
    if (report.eligibility_income or Decimal("0.00")) == Decimal("0.00"):
        report.eligibility_income = ELIGIBILITY_BONUS

    # Lock extra unpaired member on heavy side
    # You need a field like member.locked_left or member.locked_right or a separate table to mark locked nodes.
    # Example:
    # member.locked_extra_side = "left" or "right"
    # member.save()

    # Recompute total
    report.total_income = (
        (report.eligibility_income or Decimal("0.00")) +
        (report.binary_income or Decimal("0.00")) +
        (report.sponsor_income or Decimal("0.00")) +
        (report.wallet_income or Decimal("0.00")) +
        (report.salary_income or Decimal("0.00"))
    )
    report.save()

