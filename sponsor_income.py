from decimal import Decimal
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport

SPONSOR_INCOME_AMOUNT = Decimal('200.00')   # temp dummy amount - later change

def give_sponsor_income(new_member):
    """
    Sponsor income rule:
    1. If Parent == Sponsor ➝ income goes to Parent's parent (upline)
    2. Else ➝ direct Sponsor gets income
    """

    parent = new_member.parent
    sponsor = new_member.sponsor
    today = timezone.now().date()

    # If no sponsor → stop
    if not sponsor:
        return Decimal("0.00")

    # -------- Rule 1 : Parent = Sponsor --------
    if parent and sponsor and parent == sponsor:
        upline = parent.parent   # 1 level above

        if not upline:
            return Decimal("0.00")  # top person reached

        receiver = upline
    else:
        # -------- Rule 2 : normal sponsor income --------
        receiver = sponsor

    # ====== Add income to DailyIncomeReport ======
    report, created = DailyIncomeReport.objects.get_or_create(
        member=receiver,
        date=today,
        defaults={'sponsor_income': SPONSOR_INCOME_AMOUNT}
    )

    if not created:
        report.sponsor_income += SPONSOR_INCOME_AMOUNT
        report.save()

    # ====== Update total sponsor income ======
    receiver.total_sponsor_income += SPONSOR_INCOME_AMOUNT
    receiver.save()

    return SPONSOR_INCOME_AMOUNT

