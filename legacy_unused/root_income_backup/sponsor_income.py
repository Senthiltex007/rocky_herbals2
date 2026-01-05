from decimal import Decimal
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport

SPONSOR_INCOME_AMOUNT = Decimal("200.00")

def give_sponsor_income(new_member):
    """
    Sponsor income rules:
    Rule 1: If Parent == Sponsor → income goes to Parent's parent
    Rule 2: Else → direct sponsor
    Rule 3: Sponsor MUST be binary eligible (1:1 completed)
    Rule 4: No duplicate income for same member & date
    """

    today = timezone.now().date()

    parent = new_member.parent
    sponsor = new_member.sponsor

    # ❌ No sponsor → stop
    if not sponsor:
        return Decimal("0.00")

    # -------------------------------
    # Determine receiver
    # -------------------------------
    if parent and sponsor and parent == sponsor:
        receiver = parent.parent
        if not receiver:
            return Decimal("0.00")
    else:
        receiver = sponsor

    # -------------------------------
    # Eligibility check (VERY IMPORTANT)
    # -------------------------------
    if not receiver.binary_eligible:
        return Decimal("0.00")

    # -------------------------------
    # Duplicate protection
    # -------------------------------
    report, created = DailyIncomeReport.objects.get_or_create(
        member=receiver,
        date=today
    )

    # Already paid today → STOP
    if report.sponsor_income and report.sponsor_income > 0:
        return Decimal("0.00")

    # -------------------------------
    # Credit sponsor income
    # -------------------------------
    report.sponsor_income = SPONSOR_INCOME_AMOUNT
    report.save()

    # Wallet update
    receiver.sponsor_income += SPONSOR_INCOME_AMOUNT
    receiver.main_wallet += SPONSOR_INCOME_AMOUNT
    receiver.save(update_fields=["sponsor_income", "main_wallet"])

    return SPONSOR_INCOME_AMOUNT

