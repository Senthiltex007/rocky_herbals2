# ==========================================================
# 3) herbalapp/management/commands/mlm_run_today.py ✅ BEST AUTO RUN
# ==========================================================
from django.core.management.base import BaseCommand
from django.utils import timezone
from herbalapp.mlm.final_master_engine import run_full_daily_engine


class Command(BaseCommand):
    help = "Run MLM engine for today (safe single run)"

    def handle(self, *args, **options):
        run_date = timezone.localdate()
        self.stdout.write(f"🚀 Running MLM engine for {run_date}")
        run_full_daily_engine(run_date)
        self.stdout.write(self.style.SUCCESS("✅ Done"))

