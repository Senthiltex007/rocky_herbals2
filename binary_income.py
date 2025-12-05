from decimal import Decimal
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport

PAIR_AMOUNT = Decimal('500.00')        # Income per pair
DAILY_MAX_PAIRS = 5                    # Daily capping

def process_member_binary_income(member: Member):
    today = timezone.now().date()
    income_today = Decimal('0.00')

    # Total new members count including carry forward
    left_new = member.left_new_today + member.left_cf
    right_new = member.right_new_today + member.right_cf

    # ---------------------------------------------------
    # 1. FIRST ACHIEVEMENT (1:2 or 2:1) — One time only
    # ---------------------------------------------------
    if not member.binary_eligible:   # first pair condition
        if (left_new == 1 and right_new == 2) or (left_new == 2 and right_new == 1):

            # Check if direct in same leg (Sponsor = Parent)
            left_direct = all(m.sponsor_id == member.id for m in Member.objects.filter(parent=member, side='left'))
            right_direct = all(m.sponsor_id == member.id for m in Member.objects.filter(parent=member, side='right'))

            if left_direct and right_direct:
                income_today += PAIR_AMOUNT
                member.binary_eligible = True
                member.binary_eligible_date = timezone.now()
                member.save()

    # ---------------------------------------------------
    # 2. NORMAL BINARY PAIR INCOME (1:1 only after eligible)
    # ---------------------------------------------------
    if member.binary_eligible:
        pairs_today = min(left_new, right_new, DAILY_MAX_PAIRS)
        income_today += pairs_today * PAIR_AMOUNT

        # Carry forward remaining members
        member.left_cf = left_new - pairs_today
        member.right_cf = right_new - pairs_today
        member.save()

    # ---------------------------------------------------
    # 3. DAILY REPORT SAVE OR UPDATE
    # ---------------------------------------------------
    report, created = DailyIncomeReport.objects.get_or_create(
        member=member,
        date=today,
        defaults={'binary_income': income_today}
    )

    if not created:  # If already exists → Add today's amount
        report.binary_income += income_today
        report.save()

    return income_today

