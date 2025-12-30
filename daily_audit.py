import os
import sys
import django
import datetime
from django.db.models import Sum, Count

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rocky_herbals2.settings")
django.setup()

from herbalapp.models import SponsorIncome, IncomeRecord


def parse_date_arg() -> datetime.date:
    if len(sys.argv) > 1:
        return datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    return datetime.date.today()


def audit_sponsor_income(run_date: datetime.date):
    print(f"=== Daily Audit for {run_date} ===")

    # Check duplicates in SponsorIncome (same sponsor-child on same day)
    dupes_raw = SponsorIncome.objects.filter(date=run_date).values("sponsor_id", "child_id")
    seen = {}
    for d in dupes_raw:
        key = (d["sponsor_id"], d["child_id"])
        seen[key] = seen.get(key, 0) + 1
    for key, count in seen.items():
        if count > 1:
            print("Duplicate SponsorIncome found:", key, "count =", count)

    # Check mismatch between SponsorIncome sum and IncomeRecord.sponsor_income
    records = IncomeRecord.objects.filter(created_at__date=run_date).values(
        "member_id", "eligibility_income", "binary_income", "sponsor_income", "total_income"
    )
    for rec in records:
        sponsor_sum = SponsorIncome.objects.filter(
            sponsor_id=rec["member_id"], date=run_date
        ).aggregate(total_amount_sum=Sum("amount"))["total_amount_sum"] or 0

        if sponsor_sum != (rec["sponsor_income"] or 0):
            print(
                f"Mismatch for member {rec['member_id']}: "
                f"IncomeRecord sponsor_income={rec['sponsor_income']} vs SponsorIncome sum={sponsor_sum}"
            )
        else:
            print(f"Member {rec['member_id']} sponsor_income consistent ({sponsor_sum})")


def cleanup_duplicate_income_records(run_date: datetime.date, dry_run: bool = False):
    """
    Keep latest IncomeRecord per member for run_date, delete older duplicates.
    """
    print("\n=== Duplicate IncomeRecord cleanup ===")
    dupes = (
        IncomeRecord.objects.filter(created_at__date=run_date)
        .values("member_id")
        .annotate(c=Count("id"))
        .filter(c__gt=1)
    )

    count_groups = 0
    count_deleted = 0

    for d in dupes:
        member_id = d["member_id"]
        records = (
            IncomeRecord.objects
            .filter(member_id=member_id, created_at__date=run_date)
            .order_by("-created_at", "-id")
        )
        latest = records.first()
        to_delete = records[1:]  # keep latest only

        count_groups += 1
        print(f"Member {member_id} has {d['c']} records. Keeping latest id={latest.id}.")

        for rec in to_delete:
            print(f"Deleting duplicate IncomeRecord id={rec.id} for member={member_id}")
            if not dry_run:
                rec.delete()
            count_deleted += 1

    if count_groups == 0:
        print("No duplicate IncomeRecord rows found.")
    else:
        print(f"Cleanup groups={count_groups}, rows_deleted={count_deleted}, dry_run={dry_run}")


if __name__ == "__main__":
    run_date = parse_date_arg()
    audit_sponsor_income(run_date)

    # Set dry_run=True first to preview; switch to False to actually delete
    cleanup_duplicate_income_records(run_date, dry_run=False)

    print("=== Audit + Cleanup Complete ===")

