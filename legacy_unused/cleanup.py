from herbalapp.models import SponsorIncome, IncomeRecord
import datetime

run_date = datetime.date(2025, 12, 28)

dupes = SponsorIncome.objects.filter(
    sponsor__auto_id="rocky002",
    child__auto_id="rocky009",
    date=run_date
).order_by("id")

if dupes.count() > 1:
    keep = dupes.last()
    dupes.exclude(id=keep.id).delete()
    print("Cleaned duplicates, kept record:", keep.amount)

    income_record = IncomeRecord.objects.filter(
        member__auto_id="rocky002",
        created_at__date=run_date
    ).first()
    if income_record:
        income_record.sponsor_income = keep.amount
        income_record.total_income = (
            (income_record.eligibility_income or 0)
            + (income_record.binary_income or 0)
            + keep.amount
        )
        income_record.save()
        print("IncomeRecord corrected:", income_record.sponsor_income, income_record.total_income)
else:
    print("No duplicates found, DB clean.")

