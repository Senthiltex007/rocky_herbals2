# ==========================================================
# herbalapp/management/commands/mlm_run_full_daily.py
# ==========================================================

from datetime import date
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date

from herbalapp.mlm.engine_lock import run_with_lock
from herbalapp.mlm.final_master_engine import run_full_daily_engine


# ==========================================================
# Django Management Command (LOCK-SAFE)
# ==========================================================
class Command(BaseCommand):
    help = "Run FULL MLM Daily Engine safely (Binary + Eligibility + Sponsor)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Run date in YYYY-MM-DD format (optional)"
        )

    def handle(self, *args, **options):
        run_date = parse_date(options["date"]) if options.get("date") else date.today()

        self.stdout.write(f"🚀 Running MLM Master Engine for {run_date}")

        try:
            # 🔒 LOCK-SAFE execution (CRITICAL)
            run_with_lock(run_date, run_full_daily_engine)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
            return

        self.stdout.write(self.style.SUCCESS("✅ MLM Master Engine Completed Successfully"))

