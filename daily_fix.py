import datetime
from django.db.models import Sum, Count
from herbalapp.models import SponsorIncome, IncomeRecord

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

# 2. Fix mismatches between SponsorIncome sum and IncomeRecord.sponsor_income
records = IncomeRecord.objects.filter(created_at__date=run_date)

for rec in records:
    sponsor_sum = SponsorIncome.objects.filter(
        sponsor=rec.member,
        date=run_date
    ).aggregate(total_amount_sum=Sum("amount"))["total_amount_sum"] or 0

    if sponsor_sum != (rec.sponsor_income or 0):
        print(
            f"Mismatch FIXED for {rec.member.auto_id}: "
            f"IncomeRecord sponsor_income={rec.sponsor_income} → corrected to {sponsor_sum}"
        )
        rec.sponsor_income = sponsor_sum
        rec.total_income = (
            (rec.eligibility_income or 0)
            + (rec.binary_income or 0)
            + (rec.sponsor_income or 0)
            + (rec.wallet_income or 0)
            + (rec.salary_income or 0)
        )
        rec.save()
    else:
        print(f"{rec.member.auto_id} sponsor_income already consistent ({sponsor_sum})")

# 3. Cleanup duplicate IncomeRecord rows
print("\n=== Duplicate IncomeRecord cleanup ===")
dupes_ir = (
    IncomeRecord.objects.filter(created_at__date=run_date)
    .values("member_id")
    .annotate(c=Count("id"))
    .filter(c__gt=1)
)

for d in dupes_ir:
    member_id = d["member_id"]
    records = (
        IncomeRecord.objects
        .filter(member_id=member_id, created_at__date=run_date)
        .order_by("-created_at", "-id")
    )
    keep = records.first()
    to_delete = records[1:]

    print(f"Member {member_id} has {d['c']} records. Keeping latest id={keep.id}.")
    for rec in to_delete:
        print(f"Deleting duplicate IncomeRecord id={rec.id} for member={member_id}")
        rec.delete()

print("=== Daily Fix Complete ===")

