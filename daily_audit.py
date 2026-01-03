import os
import sys
import django
import datetime
from django.db.models import Sum, Count

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rocky_herbals2.settings")
django.setup()

from herbalapp.models import SponsorIncome, IncomeRecord, DailyIncomeReport


def parse_date_arg() -> datetime.date:
    if len(sys.argv) > 1:
        return datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    return datetime.date.today()


def audit_sponsor_income(run_date: datetime.date, auto_fix: bool = False):
    print(f"=== SponsorIncome Audit for {run_date} ===")

    dupes_raw = SponsorIncome.objects.filter(date=run_date).values("sponsor_id", "child_id")
    seen = {}
    for d in dupes_raw:
        key = (d["sponsor_id"], d["child_id"])
        seen[key] = seen.get(key, 0) + 1
    for key, count in seen.items():
        if count > 1:
            print("Duplicate SponsorIncome found:", key, "count =", count)
            if auto_fix:
                qs = SponsorIncome.objects.filter(
                    sponsor_id=key[0], child_id=key[1], date=run_date
                ).order_by("id")
                keep = qs.last()
                qs.exclude(id=keep.id).delete()
                print(f"Cleaned SponsorIncome duplicates for {key}, kept id={keep.id}, amount={keep.amount}")
    if not seen:
        print("No SponsorIncome rows found for this date.")


def audit_income_records(run_date: datetime.date, auto_fix: bool = False):
    print(f"\n=== IncomeRecord Audit for {run_date} ===")
    records = IncomeRecord.objects.filter(date=run_date)
    if not records.exists():
        print("No IncomeRecord rows found.")
    for rec in records:
        calc_total = (
            (rec.eligibility_income or 0)
            + (rec.binary_income or 0)
            + (rec.wallet_income or 0)
            + (rec.sponsor_income or 0)   # ✅ include sponsor income
        )
        if calc_total != (rec.total_income or 0):
            print(f"Mismatch for IncomeRecord {rec.id}: stored={rec.total_income}, calc={calc_total}")
            if auto_fix:
                rec.total_income = calc_total
                rec.save(update_fields=["total_income"])
                print(f"Fixed IncomeRecord {rec.id} total → {calc_total}")
        else:
            print(
                f"Member {rec.member_id}: eligibility={rec.eligibility_income}, "
                f"binary={rec.binary_income}, sponsor={rec.sponsor_income}, "
                f"wallet={rec.wallet_income}, total={rec.total_income} (consistent)"
            )


def audit_daily_report(run_date: datetime.date, auto_fix: bool = False):
    print(f"\n=== DailyIncomeReport Audit for {run_date} ===")
    reports = DailyIncomeReport.objects.filter(date=run_date)
    if not reports.exists():
        print("No DailyIncomeReport rows found.")
    for r in reports:
        calc_total = (
            (r.binary_income or 0)
            + (r.sponsor_income or 0)
            + (r.wallet_income or 0)
            + (r.salary_income or 0)
            + (r.eligibility_income or 0)
        )
        if calc_total != (r.total_income or 0):
            print(f"Mismatch for member {r.member_id}: stored={r.total_income}, calc={calc_total}")
            if auto_fix:
                r.total_income = calc_total
                r.save(update_fields=["total_income"])
                print(f"Fixed DailyIncomeReport {r.id} total → {calc_total}")
        else:
            print(f"Member {r.member_id} report consistent (total={r.total_income})")


def cleanup_duplicate_income_records(run_date: datetime.date, dry_run: bool = True):
    print("\n=== Duplicate IncomeRecord cleanup ===")
    dupes = (
        IncomeRecord.objects.filter(date=run_date)
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
            .filter(member_id=member_id, date=run_date)
            .order_by("-id")
        )
        latest = records.first()
        to_delete = records[1:]

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
    audit_sponsor_income(run_date, auto_fix=True)
    audit_income_records(run_date, auto_fix=True)
    audit_daily_report(run_date, auto_fix=True)

    # Set dry_run=True first to preview; switch to False to actually delete
    cleanup_duplicate_income_records(run_date, dry_run=False)

    print("=== Audit + Auto-Fix Complete ===")

