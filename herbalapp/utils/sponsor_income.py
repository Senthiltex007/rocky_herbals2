from decimal import Decimal
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport

SPONSOR_AMOUNT = Decimal('500.00')   # equal to binary income

def give_sponsor_income(member):
    """
    member = binary income received member
    sponsor = member.sponsor (refer id)
    """

    if not member.sponsor:
        return 0   # No sponsor so no income

    sponsor = member.sponsor

    # sponsor must be binary eligible
    if not sponsor.binary_eligible:
        return 0   # Rule 2: only eligible sponsors earn

    today = timezone.now().date()

    # save sponsor income in daily report
    report, created = DailyIncomeReport.objects.get_or_create(
        member=sponsor,
        date=today,
        defaults={'sponsor_income': SPONSOR_AMOUNT}
    )

    if not created:
        report.sponsor_income += SPONSOR_AMOUNT
        report.save()

    # add total income in sponsor profile
    sponsor.total_sponsor_income += SPONSOR_AMOUNT
    sponsor.save(update_fields=["total_sponsor_income"])

    print(f"✅ Sponsor income credited: {sponsor.member_id} +{SPONSOR_AMOUNT}")
    return SPONSOR_AMOUNT

