# herbalapp/tasks.py
# ----------------------------------------------------------
# ✅ Daily Engine Runner + Audit Trigger
# ----------------------------------------------------------

from datetime import date
from django.core.management.base import BaseCommand
from herbalapp.models import Member
from herbalapp.engine.run import process_member_daily
from herbalapp.audit_full_income import run_full_income_audit


class Command(BaseCommand):
    help = "Run daily MLM engine for all root members + audit incomes"

    def handle(self, *args, **options):
        run_date = date.today()
        self.stdout.write(self.style.NOTICE(f"🚀 Starting daily engine run for {run_date}"))

        # Run engine for all root members
        for root in Member.objects.filter(placement__isnull=True):
            try:
                process_member_daily(root, run_date)
                self.stdout.write(self.style.SUCCESS(f"✅ Engine run for root {root.member_id}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"⚠️ Engine failed for {root.member_id}: {e}"))

        # Run full audit after engine
        self.stdout.write(self.style.NOTICE("🔍 Running full income audit..."))
        run_full_income_audit()

        self.stdout.write(self.style.SUCCESS("🎯 Daily engine + audit completed."))

