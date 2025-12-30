from django.db.models import Count

def cleanup_duplicate_income_records(run_date: datetime.date):
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

    for d in dupes:
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

