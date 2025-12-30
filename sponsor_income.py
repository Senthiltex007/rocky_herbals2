from decimal import Decimal
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport, SponsorIncome

def give_sponsor_income(new_member, child_total_for_sponsor: Decimal):
    """
    Sponsor income rules:
    1. If Parent == Sponsor ➝ income goes to Parent's parent (upline)
    2. Else ➝ direct Sponsor gets income
    3. Sponsor must have completed 1:1 pair (has_completed_first_pair = True)
    4. Amount = child_total_for_sponsor (from engine)
    """

    parent = new_member.parent
    sponsor = new_member.sponsor
    today = timezone.now().date()

    if not sponsor:
        return Decimal("0.00")

    # -------- Rule 1 : Parent = Sponsor --------
    if parent and sponsor and parent == sponsor:
        upline = parent.parent
        if not upline:
            return Decimal("0.00")
        receiver = upline
    else:
        receiver = sponsor

    # -------- Rule 3 : eligibility check --------
    if not getattr(receiver, "has_completed_first_pair", False):
        return Decimal("0.00")

    # -------- Rule 4 : prevent duplicate sponsor income --------
    exists = SponsorIncome.objects.filter(
        sponsor=receiver,
        child=new_member,
        date=today
    ).exists()

    if not exists and child_total_for_sponsor > 0:
        SponsorIncome.objects.create(
            sponsor=receiver,
            child=new_member,
            amount=child_total_for_sponsor,
            date=today
        )

        report, created = DailyIncomeReport.objects.get_or_create(
            member=receiver,
            date=today,
            defaults={'sponsor_income': child_total_for_sponsor}
        )
        if not created:
            report.sponsor_income += child_total_for_sponsor
            report.save()

        receiver.total_sponsor_income += child_total_for_sponsor
        receiver.save()

    return child_total_for_sponsor

