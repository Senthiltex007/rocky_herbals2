from decimal import Decimal
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport

PAIR_AMOUNT = Decimal('500.00')  # per pair binary income
DAILY_MAX_PAIRS = 5

def give_sponsor_income(member, amount):
    """Sponsor income credit function"""
    if not member.sponsor:
        return Decimal('0.00')

    sponsor = member.sponsor

    # Sponsor should be eligible for binary income
    if not sponsor.binary_eligible:
        return Decimal('0.00')

    today = timezone.now().date()
    report, created = DailyIncomeReport.objects.get_or_create(
        member=sponsor,
        date=today,
        defaults={'sponsor_income': amount}
    )
    if not created:
        report.sponsor_income += amount
        report.save()

    sponsor.total_sponsor_income += amount
    sponsor.save()
    return amount

def process_member_binary_income(member: Member):
    today = timezone.now().date()
    income_today = Decimal('0.00')

    # New members in left/right + carry forward
    left_new = member.left_new_today + member.left_cf
    right_new = member.right_new_today + member.right_cf

    # ----- First Achievement (1:2 or 2:1) -----
    if not member.binary_eligible:
        if (left_new == 1 and right_new == 2) or (left_new == 2 and right_new == 1):
            left_direct = all(m.sponsor_id == member.id for m in Member.objects.filter(parent=member, side='left'))
            right_direct = all(m.sponsor_id == member.id for m in Member.objects.filter(parent=member, side='right'))

            if left_direct and right_direct:
                income_today += PAIR_AMOUNT
                member.binary_eligible = True
                member.binary_eligible_date = timezone.now()
                member.save()

    # ----- Daily 1:1 Income -----
    if member.binary_eligible:
        pairs_today = min(left_new, right_new, DAILY_MAX_PAIRS)
        pair_income = pairs_today * PAIR_AMOUNT
        income_today += pair_income

        # carry forward calculation
        member.left_cf = left_new - pairs_today
        member.right_cf = right_new - pairs_today
        member.save()

    # ----- Save Daily Binary Report -----
    report, created = DailyIncomeReport.objects.get_or_create(
        member=member,
        date=today,
        defaults={'binary_income': income_today}
    )
    if not created:
        report.binary_income += income_today
        report.save()

    # ----- Sponsor Income -----
    if income_today > 0:
        give_sponsor_income(member, income_today)

    return income_today

