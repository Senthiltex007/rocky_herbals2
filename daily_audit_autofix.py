import datetime
from django.db.models import Count
from herbalapp.models import IncomeRecord

def cleanup_duplicate_income_records(run_date: datetime.date, dry_run: bool = True):
    """
    Keep latest IncomeRecord per member for run_date, delete older duplicates.
    Also auto-fix total_income consistency.
    """
    print("\n=== Duplicate IncomeRecord cleanup ===")
    dupes = (
        IncomeRecord.objects.filter(date=run_date)
        .values("member_id")
        .annotate(c=Count("id"))
        .filter(c__gt=1)
    )

    count_groups = 0
    count_deleted = 0
    count_fixed_totals = 0

    for d in dupes:
        member_id = d["member_id"]
        records = (
            IncomeRecord.objects
            .filter(member_id=member_id, date=run_date)
            .order_by("-id")
        )
        keep = records.first()
        to_delete = records[1:]

        count_groups += 1
        print(f"Member {member_id} has {d['c']} records. Keeping latest id={keep.id}.")

        # ✅ Auto-fix totals for the kept record
        calc_total = (
            (keep.eligibility_income or 0)
            + (keep.binary_income or 0)
            + (keep.wallet_income or 0)
            + (keep.sponsor_income or 0)
        )
        if calc_total != (keep.total_income or 0):
            print(f"Fixing IncomeRecord {keep.id} total from {keep.total_income} → {calc_total}")
            if not dry_run:
                keep.total_income = calc_total
                keep.save(update_fields=["total_income"])
            count_fixed_totals += 1

        # Delete duplicates
        for rec in to_delete:
            print(f"Deleting duplicate IncomeRecord id={rec.id} for member={member_id}")
            if not dry_run:
                rec.delete()
            count_deleted += 1

    if count_groups == 0:
        print("No duplicate IncomeRecord rows found.")
    else:
        print(f"Cleanup groups={count_groups}, rows_deleted={count_deleted}, totals_fixed={count_fixed_totals}, dry_run={dry_run}")

