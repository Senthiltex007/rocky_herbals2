# ==========================================================
# herbalapp/management/commands/mlm_run_full_daily.py
# FINAL VERSION WITH AUTO-AUDIT
# ==========================================================

from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from django.db import transaction
from django.utils import timezone

from herbalapp.models import Member, DailyIncomeReport
from herbalapp.mlm_engine_binary_runner import run_binary_engine
from herbalapp.mlm.sponsor_engine import run_sponsor_engine
from herbalapp.mlm.audit import print_audit_summary

ROOT_ID = "rocky004"

# ----------------------------------------------------------
# FULL DAILY ENGINE
# ----------------------------------------------------------
@transaction.atomic
def run_full_daily_engine(run_date: date):
    members = Member.objects.exclude(auto_id=ROOT_ID).order_by("id")

    # -----------------------------
    # 1️⃣ Binary + Eligibility
    # -----------------------------
    for member in members:
        report, _ = DailyIncomeReport.objects.get_or_create(
            member=member,
            date=run_date
        )

        run_binary_engine(member, run_date)

        # Update total safely
        report.refresh_from_db()
        report.total_income = (
            report.binary_income +
            report.binary_eligibility_income +
            report.sponsor_income +
            getattr(report, "flashout_wallet_income", Decimal("0"))
        )
        report.save(update_fields=["total_income"])

    # -----------------------------
    # 2️⃣ Sponsor Income
    # -----------------------------
    for member in members:
        run_sponsor_engine(member, run_date)

    # -----------------------------
    # 3️⃣ Final Total Update
    # -----------------------------
    for report in DailyIncomeReport.objects.filter(date=run_date):
        report.total_income = (
            report.binary_income +
            report.binary_eligibility_income +
            report.sponsor_income +
            getattr(report, "flashout_wallet_income", Decimal("0"))
        )
        report.save(update_fields=["total_income"])

    # -----------------------------
    # 4️⃣ AUTO AUDIT AFTER DAILY ENGINE
    # -----------------------------
    print_audit_summary(run_date)

# ----------------------------------------------------------
# Django Management Command
# ----------------------------------------------------------
class Command(BaseCommand):
    help = "Run FULL MLM Daily Engine (Binary + Sponsor) with Auto-Audit"

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, help="YYYY-MM-DD")

    def handle(self, *args, **options):
        run_date = parse_date(options["date"]) if options.get("date") else date.today()
        self.stdout.write(f"🚀 Running MLM Engine for {run_date}")

        try:
            run_full_daily_engine(run_date)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
            return

        self.stdout.write(self.style.SUCCESS("✅ MLM Daily Engine Completed with Audit"))

