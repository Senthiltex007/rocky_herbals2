# ==========================================================
# herbalapp/management/commands/test_mlm_income.py
# Quick MLM Income Test Script
# ==========================================================
from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from herbalapp.models import Member, DailyIncomeReport
from herbalapp.management.commands.mlm_run_full_daily import run_full_daily_engine

ROOT_ID = "rocky001"

class Command(BaseCommand):
    help = "Test MLM Daily Engine - Binary + Sponsor Income"

    def handle(self, *args, **options):
        run_date = date.today()
        self.stdout.write(f"🚀 Running TEST MLM Engine for {run_date}")

        # Run full engine
        run_full_daily_engine(run_date)

        # --------------------------------------------------
        # Check ROOT member
        # --------------------------------------------------
        try:
            root = Member.objects.get(auto_id=ROOT_ID)
            root_report = DailyIncomeReport.objects.get(member=root, date=run_date)
            if root_report.total_income > 0:
                self.stdout.write(self.style.ERROR(f"❌ ROOT {ROOT_ID} incorrectly got income!"))
            else:
                self.stdout.write(self.style.SUCCESS(f"✅ ROOT {ROOT_ID} correctly skipped."))
        except Member.DoesNotExist:
            self.stdout.write(self.style.WARNING(f"⚠ ROOT {ROOT_ID} not found."))
        except DailyIncomeReport.DoesNotExist:
            self.stdout.write(self.style.SUCCESS(f"✅ ROOT {ROOT_ID} has no income report as expected."))

        # --------------------------------------------------
        # Check all other members
        # --------------------------------------------------
        members = Member.objects.exclude(auto_id=ROOT_ID)
        for m in members:
            report = DailyIncomeReport.objects.get(member=m, date=run_date)
            self.stdout.write(f"Member {m.member_id}: Binary={report.binary_income}, Eligibility={report.binary_eligibility_income}, Sponsor={report.sponsor_income}, Total={report.total_income}")

        self.stdout.write(self.style.SUCCESS("✅ Test MLM Engine Completed"))

