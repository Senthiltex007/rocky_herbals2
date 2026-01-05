import os
import django
import datetime
from django.db import transaction
from django.db.models import Count

# -------------------------------------------------
# Django setup (important for standalone script)
# -------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rocky_herbals2.settings")
django.setup()

from herbalapp.models import IncomeRecord


def cleanup_duplicate_income_records(
    run_date: datetime.date,
    dry_run: bool = True
):
    """
    Keep latest IncomeRecord per member for run_date,
    delete older duplicates,
    and auto-fix total_income.
    """

    print("\n=== Duplicate IncomeRecord Cleanup ===")
    print(f"Run date : {run_date}")
    print(f"Dry run  : {dry_run}")

    dupes = (
        IncomeRecord.objects
        .filter(date=run_date)
        .values("auto_id")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
    )

    if not dupes.exists():
        print("✅ No duplicate IncomeRecord rows found.")
        return

    total_groups = 0
    total_deleted = 0
    total_fixed = 0

    with transaction.atomic():
        for d in dupes:
            auto_id = d["auto_id"]

            records = (
                IncomeRecord.objects
                .filter(auto_id=auto_id, date=run_date)
                .order_by("-id")  # latest first
            )

            keep = records.first()
            duplicates = records[1:]

            total_groups += 1
            print(
                f"\nMember {auto_id} "
                f"has {d['count']} records → keeping id={keep.id}"
            )

            # ---------------------------------
            # Auto-fix total_income
            # ---------------------------------
            calculated_total = (
                (keep.eligibility_income or 0)
                + (keep.binary_income or 0)
                + (keep.wallet_income or 0)
                + (keep.sponsor_income or 0)
            )

            if calculated_total != (keep.total_income or 0):
                print(
                    f" Fixing total_income: "
                    f"{keep.total_income} → {calculated_total}"
                )
                if not dry_run:
                    keep.total_income = calculated_total
                    keep.save(update_fields=["total_income"])
                total_fixed += 1
            else:
                print(" total_income OK")

            # ---------------------------------
            # Delete duplicates
            # ---------------------------------
            for rec in duplicates:
                print(f" Deleting duplicate record id={rec.id}")
                if not dry_run:
                    rec.delete()
                total_deleted += 1

    print("\n=== Cleanup Summary ===")
    print(f"Groups processed : {total_groups}")
    print(f"Records deleted  : {total_deleted}")
    print(f"Totals fixed     : {total_fixed}")
    print(f"Dry run          : {dry_run}")
    print("=== Cleanup Complete ===")

