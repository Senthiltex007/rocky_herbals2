from datetime import date
from django.db.models import Sum
from herbalapp.models import DailyIncomeReport

def run(*args):
    if args:
        run_date = date.fromisoformat(args[0])
    else:
        run_date = date.today()

    print(f"Running daily audit autofix for {run_date}")

    records = DailyIncomeReport.objects.filter(date=run_date)

    if not records.exists():
        print("No DailyIncomeReport records found for this date.")
        return

    totals = records.aggregate(
        total_eligibility=Sum("eligibility_income"),
        total_binary=Sum("binary_income"),
        total_sponsor=Sum("sponsor_income"),
        total_wallet=Sum("wallet_income"),
        total_salary=Sum("salary_income"),
        grand_total=Sum("total_income"),
    )

    print("Totals for", run_date)
    for key, value in totals.items():
        print(f"{key}: {value or 0}")

