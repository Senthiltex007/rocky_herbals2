import os
import sys
import django
import datetime
import logging
from django.db import transaction
from django.db.models import Sum, Count

# ------------------------------------------------------------------
# Django setup
# ------------------------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rocky_herbals2.settings")
django.setup()

from herbalapp.models import SponsorIncome, IncomeRecord, DailyIncomeReport

# ------------------------------------------------------------------
# Logging setup (cron safe)
# ------------------------------------------------------------------
logging.basicConfig(
    filename="daily_audit.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def parse_date_arg() -> datetime.date:
    if len(sys.argv) > 1:
        return datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    return datetime.date.today()


# ------------------------------------------------------------------
# SponsorIncome Audit
# ------------------------------------------------------------------
def audit_sponsor_income(run_date: datetime.date, auto_fix: bool = False):
    logging.info(f"=== SponsorIncome Audit for {run_date} ===")
    print(f"=== SponsorIncome Audit for {run_date} ===")

    dupes_raw = (
        SponsorIncome.objects
        .filter(date=run_date)
        .values("sponsor_id", "child_id", "date")
    )

    seen = {}
    for d in dupes_raw:
        key = (d["sponsor_id"], d["child_id"], d["date"])
        seen[key] = seen.get(key, 0) + 1

    if not seen:
        print("No SponsorIncome rows found for this date.")
        logging.info("No SponsorIncome rows found for this date.")
        return

    with transaction.atomic():
        for key, count in seen.items():
            if count > 1:
                msg = f"Duplicate SponsorIncome found: {key}, count={count}"
                print(msg)
                logging.warning(msg)

                if auto_fix:
                    qs = (
                        SponsorIncome.objects
                        .filter(
                            sponsor_id=key[0],
                            child_id=key[1],
                            date=key[2]
                        )
                        .order_by("id")
                    )
                    keep = qs.last()
                    qs.exclude(id=keep.id).delete()

                    fix_msg = (
                        f"Cleaned SponsorIncome duplicates for {key}, "
                        f"kept id={keep.id}, amount={keep.amount}"
                    )
                    print(fix_msg)
                    logging.info(fix_msg)


# ------------------------------------------------------------------
# IncomeRecord Audit
# ------------------------------------------------------------------
def audit_income_records(run_date: datetime.date, auto_fix: bool = False):
    logging.info(f"=== IncomeRecord Audit for {run_date} ===")
    print(f"\n=== IncomeRecord Audit for {run_date} ===")

    records = IncomeRecord.objects.filter(date=run_date)
    if not records.exists():
        print("No IncomeRecord rows found.")
        logging.info("No IncomeRecord rows found.")
        return

    with transaction.atomic():
        for rec in records:
            calc_total = (
                (rec.eligibility_income or 0)
                + (rec.binary_income or 0)
                + (rec.wallet_income or 0)
                + (rec.sponsor_income or 0)
            )

            if calc_total != (rec.total_income or 0):
                msg = (
                    f"Mismatch IncomeRecord id={rec.id}: "
                    f"stored={rec.total_income}, calc={calc_total}"
                )
                print(msg)
                logging.warning(msg)

                if auto_fix:
                    rec.total_income = calc_total
                    rec.save(update_fields=["total_income"])
                    fix_msg = f"Fixed IncomeRecord {rec.id} total → {calc_total}"
                    print(fix_msg)
                    logging.info(fix_msg)
            else:
                ok_msg = (
                    f"Member {rec.auto_id}: "
                    f"eligibility={rec.eligibility_income}, "
                    f"binary={rec.binary_income}, "
                    f"sponsor={rec.sponsor_income}, "
                    f"wallet={rec.wallet_income}, "
                    f"total={rec.total_income} (OK)"
                )
                print(ok_msg)
                logging.info(ok_msg)


# ------------------------------------------------------------------
# DailyIncomeReport Audit
# ------------------------------------------------------------------
def audit_daily_report(run_date: datetime.date, auto_fix: bool = False):
    logging.info(f"=== DailyIncomeReport Audit for {run_date} ===")
    print(f"\n=== DailyIncomeReport Audit for {run_date} ===")

    reports = DailyIncomeReport.objects.filter(date=run_date)
    if not reports.exists():
        print("No DailyIncomeReport rows found.")
        logging.info("No DailyIncomeReport rows found.")
        return

    with transaction.atomic():
        for r in reports:
            calc_total = (
                (r.binary_income or 0)
                + (r.sponsor_income or 0)
                + (r.wallet_income or 0)
                + (r.salary_income or 0)
                + (r.eligibility_income or 0)
            )

            if calc_total != (r.total_income or 0):
                msg = (
                    f"Mismatch DailyIncomeReport member={r.auto_id}: "
                    f"stored={r.total_income}, calc={calc_total}"
                )
                print(msg)
                logging.warning(msg)

                if auto_fix:
                    r.total_income = calc_total
                    r.save(update_fields=["total_income"])
                    fix_msg = f"Fixed DailyIncomeReport {r.id} total → {calc_total}"
                    print(fix_msg)
                    logging.info(fix_msg)
            else:
                ok_msg = (
                    f"Member {r.auto_id} report OK "
                    f"(total={r.total_income})"
                )
                print(ok_msg)
                logging.info(ok_msg)


# ------------------------------------------------------------------
# Duplicate IncomeRecord Cleanup
# ------------------------------------------------------------------
def cleanup_duplicate_income_records(run_date: datetime.date, dry_run: bool = True):
    logging.info("=== Duplicate IncomeRecord cleanup ===")
    print("\n=== Duplicate IncomeRecord cleanup ===")

    dupes = (
        IncomeRecord.objects
        .filter(date=run_date)
        .values("auto_id")
        .annotate(c=Count("id"))
        .filter(c__gt=1)
    )

    if not dupes.exists():
        print("No duplicate IncomeRecord rows found.")
        logging.info("No duplicate IncomeRecord rows found.")
        return

    with transaction.atomic():
        for d in dupes:
            auto_id = d["auto_id"]
            records = (
                IncomeRecord.objects
                .filter(auto_id=auto_id, date=run_date)
                .order_by("-id")
            )

            latest = records.first()
            to_delete = records[1:]

            msg = (
                f"Member {auto_id} has {d['c']} records. "
                f"Keeping latest id={latest.id}"
            )
            print(msg)
            logging.warning(msg)

            for rec in to_delete:
                del_msg = f"Deleting duplicate IncomeRecord id={rec.id}"
                print(del_msg)
                logging.warning(del_msg)

                if not dry_run:
                    rec.delete()


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
if __name__ == "__main__":
    run_date = parse_date_arg()

    audit_sponsor_income(run_date, auto_fix=True)
    audit_income_records(run_date, auto_fix=True)
    audit_daily_report(run_date, auto_fix=True)

    # First time keep dry_run=True, then set False
    cleanup_duplicate_income_records(run_date, dry_run=False)

    print("=== Audit + Auto-Fix Complete ===")
    logging.info("=== Audit + Auto-Fix Complete ===")

