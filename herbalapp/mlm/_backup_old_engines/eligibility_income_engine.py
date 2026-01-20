# ==========================================================
# herbalapp/management/commands/mlm_run_full_daily.py
# Fully integrated: Eligibility + Binary + Flashout + Sponsor + Audit
# ==========================================================

from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from django.db import transaction

from herbalapp.models import Member, DailyIncomeReport
from herbalapp.mlm.eligibility_income_engine import process_binary_eligibility
from herbalapp.mlm.binary_engine import run_binary_engine
from herbalapp.mlm.flashout_engine import run_flashout_engine
from herbalapp.mlm.audit import print_audit_summary
from herbalapp.mlm.daily_income_engine import calculate_daily_income

ROOT_ID = "rocky004"
ELIGIBILITY_BONUS = Decimal("500")


# ----------------------------------------------------------
# Determine sponsor receiver (rules 1,2,3)
# ----------------------------------------------------------
def get_sponsor_receiver(child: Member):
    if not child.sponsor:
        return None
    if child.sponsor.auto_id == ROOT_ID:
        return None
    if child.placement_id and child.sponsor_id:
        if child.placement_id == child.sponsor_id:
            if child.placement and child.placement.parent:
                if child.placement.parent.auto_id != ROOT_ID:
                    return child.placement.parent
            return None
        else:
            return child.sponsor
    return None


# ----------------------------------------------------------
# Sponsor Engine
# ----------------------------------------------------------
@transaction.atomic
def run_sponsor_engine(run_date: date):
    members = Member.objects.exclude(auto_id=ROOT_ID).order_by("id")

    for child in members:
        try:
            report = DailyIncomeReport.objects.get(member=child, date=run_date)
        except DailyIncomeReport.DoesNotExist:
            continue

        if report.sponsor_processed:
            continue

        # Sponsor income = eligibility + binary income
        child_amount = (report.binary_eligibility_income or Decimal("0.00")) + \
                       (report.binary_income or Decimal("0.00"))
        if child_amount <= 0:
            continue

        sponsor = get_sponsor_receiver(child)
        if not sponsor or not sponsor.binary_eligible:
            continue

        # Credit sponsor
        sponsor.main_wallet += child_amount
        sponsor.sponsor_income += child_amount
        sponsor.save(update_fields=["main_wallet", "sponsor_income"])

        sponsor_report, created = DailyIncomeReport.objects.get_or_create(
            member=sponsor,
            date=run_date,
            defaults={"sponsor_income": child_amount}
        )
        if not created:
            sponsor_report.sponsor_income += child_amount
            calculate_daily_income(sponsor_report)
            sponsor_report.save(update_fields=["sponsor_income","total_income"])

        # Mark child as processed
        report.sponsor_processed = True
        report.save(update_fields=["sponsor_processed"])


# ----------------------------------------------------------
# Full Daily Engine Command
# ----------------------------------------------------------
class Command(BaseCommand):
    help = "Run FULL MLM Daily Engines (Eligibility + Binary + Flashout + Sponsor + Audit)"

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, help="YYYY-MM-DD (default today)")

    def handle(self, *args, **options):
        run_date = parse_date(options["date"]) if options.get("date") else date.today()
        self.stdout.write(f"🚀 Running FULL MLM Daily Engine for {run_date}")

        members = Member.objects.exclude(auto_id=ROOT_ID).order_by("id")

        # -------------------------
        # 1️⃣ Eligibility Income Engine
        # -------------------------
        self.stdout.write("🔹 Running Eligibility Income Engine...")
        for member in members:
            try:
                process_binary_eligibility(member, run_date)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Eligibility failed for {member.auto_id}: {e}")
                )

        # -------------------------
        # 2️⃣ Binary Income Engine
        # -------------------------
        self.stdout.write("🔹 Running Binary Income Engine...")
        for member in members:
            try:
                run_binary_engine(member, run_date)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Binary failed for {member.auto_id}: {e}"))

        # -------------------------
        # 3️⃣ Flashout Engine
        # -------------------------
        self.stdout.write("🔹 Running Flashout Engine...")
        try:
            run_flashout_engine(run_date)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Flashout failed: {e}"))

        # -------------------------
        # 4️⃣ Sponsor Engine
        # -------------------------
        self.stdout.write("🔹 Running Sponsor Engine...")
        try:
            run_sponsor_engine(run_date)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Sponsor Engine failed: {e}"))

        # -------------------------
        # 5️⃣ Audit / Daily Summary
        # -------------------------
        self.stdout.write("🔹 Running Audit Summary...")
        try:
            print_audit_summary(run_date)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Audit failed: {e}"))

        self.stdout.write(self.style.SUCCESS("🎯 FULL MLM Daily Engine Completed"))

