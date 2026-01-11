# herbalapp/engine/core.py
from datetime import date
from herbalapp.models import Member, DailyIncomeReport, Income

def calculate_member_income_for_day(member: Member, run_date=None):
    """
    This function calculates:
    - Binary income
    - Sponsor income
    - Flashout bonus
    - Carry forward
    Rules applied as per your specification
    """
    if run_date is None:
        run_date = date.today()

    # Example placeholder logic — replace with full rules
    # Check if member is binary eligible today
    # Apply sponsor income rules
    # Apply binary income rules (max 5 pairs/day)
    # Apply flashout bonus rules (max 9 flashout units/day)
    # Update DailyIncomeReport
    # Update Income table

    # Check if report exists for today (avoid duplicate)
    report, created = DailyIncomeReport.objects.get_or_create(
        member=member,
        date=run_date
    )

    # Your calculation logic here
    # report.binary_income = ...
    # report.sponsor_income = ...
    # report.flashout_wallet_income = ...
    # report.total_income = sum(...)
    report.save()

