from datetime import date
from herbalapp.models import Member, DailyIncomeReport

def run(*args):
    if args:
        run_date = date.fromisoformat(args[0])
    else:
        run_date = date.today()

    print(f"Running daily fix for {run_date}")

    all_ids = set(Member.objects.values_list("auto_id", flat=True))
    report_ids = set(DailyIncomeReport.objects.filter(date=run_date).values_list("member__auto_id", flat=True))
    missing_ids = all_ids - report_ids

    for auto_id in missing_ids:
        try:
            member = Member.objects.get(auto_id=auto_id)
            DailyIncomeReport.objects.create(
                member=member,
                date=run_date,
                eligibility_income=0.0,
                binary_income=0.0,
                sponsor_income=0.0,
                wallet_income=0.0,
                salary_income=0.0,
                total_income=0.0,
            )
            print(f"Created DailyIncomeReport for {auto_id}")
        except Member.DoesNotExist:
            print(f"Member {auto_id} not found — skipped.")

