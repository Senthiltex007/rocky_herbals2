import datetime
from django.db.models import Sum, Count
from herbalapp.models import SponsorIncome, IncomeRecord, DailyIncomeReport

run_date = datetime.date.today()

print("=== Daily Fix for", run_date, "===")

# 1. Fix duplicates in SponsorIncome
dupes = SponsorIncome.objects.filter(date=run_date).values("sponsor_id", "child_id").order_by("sponsor_id", "child_id")

seen = {}
for d in dupes:
    key = (d["sponsor_id"], d["child_id"])
    seen.setdefault(key, []).append(d)

for key, records in seen.items():
    if len(records) > 1:
        sponsor_id, child_id = key
        dupes_qs = SponsorIncome.objects.filter(
            sponsor_id=sponsor_id,
            child_id=child_id,
            date=run_date
        ).order_by("id")
        keep = dupes_qs.last()
        dupes_qs.exclude(id=keep.id).delete()
        print(f"Duplicate cleaned for Sponsor={sponsor_id}, Child={child_id}. Kept amount={keep.amount}")

# 2. Audit IncomeRecord totals (✅ include sponsor_income)
records = IncomeRecord.objects.filter(date=run_date)
for rec in records:
    calc_total = (
        (rec.eligibility_income or 0)
        + (rec.binary_income or 0)
        + (rec.wallet_income or 0)
        + (rec.sponsor_income or 0)   # ✅ added sponsor income
    )
    if calc_total != (rec.total_income or 0):
        print(f"Fixing IncomeRecord {rec.id} total from {rec.total_income} → {calc_total}")
        rec.total_income = calc_total
        rec.save()
    else:
        print(f"IncomeRecord {rec.id} already consistent (total={rec.total_income})")

# 3. Audit DailyIncomeReport totals
reports = DailyIncomeReport.objects.filter(date=run_date)
for r in reports:
    calc_total = (
        (r.binary_income or 0)
        + (r.sponsor_income or 0)
        + (r.wallet_income or 0)
        + (r.salary_income or 0)
        + (r.eligibility_income or 0)
    )
    if calc_total != (r.total_income or 0):
        print(f"Fixing DailyIncomeReport {r.id} total from {r.total_income} → {calc_total}")
        r.total_income = calc_total
        r.save()
    else:
        print(f"DailyIncomeReport {r.id} consistent (total={r.total_income})")

# 4. Cleanup duplicate IncomeRecord rows
print("\n=== Duplicate IncomeRecord cleanup ===")
dupes_ir = (
    IncomeRecord.objects.filter(date=run_date)
    .values("member_id")
    .annotate(c=Count("id"))
    .filter(c__gt=1)
)

for d in dupes_ir:
    member_id = d["member_id"]
    records = (
        IncomeRecord.objects
        .filter(member_id=member_id, date=run_date)
        .order_by("-id")
    )
    keep = records.first()
    to_delete = records[1:]

    print(f"Member {member_id} has {d['c']} records. Keeping latest id={keep.id}.")
    for rec in to_delete:
        print(f"Deleting duplicate IncomeRecord id={rec.id} for member={member_id}")
        rec.delete()

print("=== Daily Fix Complete ===")

