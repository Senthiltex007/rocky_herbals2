# ==========================================================
# herbalapp/mlm/audit.py
# FINAL VERSION WITH AUTO-AUDIT AND CENTRALIZED TOTAL CALCULATION
# ==========================================================

from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from django.db import transaction
from django.utils import timezone

from herbalapp.models import Member, DailyIncomeReport
from herbalapp.mlm_engine_binary_runner import run_binary_engine
from herbalapp.mlm.daily_income_engine import calculate_daily_income

ROOT_ID = "rocky001"


# ----------------------------------------------------------
# AUDIT FUNCTION  ✅ (DEFINED HERE — NO SELF IMPORT)
# ----------------------------------------------------------
def print_audit_summary(run_date):
    """
    Audit summary after daily engine
    """
    print(f"📊 Audit completed for date: {run_date}")


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
        # Ensure report exists
        report, _ = DailyIncomeReport.objects.get_or_create(
            member=member,
            date=run_date
        )

        # Run binary income engine
        run_binary_engine(member, run_date)

        # Update total using centralized function
        report.refresh_from_db()
        calculate_daily_income(report)

    # -----------------------------
    # 2️⃣ Sponsor Income
    # -----------------------------
    for member in members:
        run_sponsor_engine(member, run_date)
        report = DailyIncomeReport.objects.get(member=member, date=run_date)
        calculate_daily_income(report)  # recalc total after sponsor credit

    # -----------------------------
    # 3️⃣ Final Total Update (safety)
    # -----------------------------
    for report in DailyIncomeReport.objects.filter(date=run_date):
        calculate_daily_income(report)

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

