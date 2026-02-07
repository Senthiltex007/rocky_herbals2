# herbalapp/management/commands/force_run_daily.py

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from datetime import date

from herbalapp.models import EngineLock
from herbalapp.mlm.final_master_engine import run_full_daily_engine


class Command(BaseCommand):
    help = "FORCE RUN MLM Engine safely for a specific date (duplicate-safe)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Date to run engine (YYYY-MM-DD)"
        )

    def handle(self, *args, **options):
        # ✅ Set run_date
        run_date = parse_date(options["date"]) if options.get("date") else date.today()
        if run_date is None:
            self.stdout.write(self.style.ERROR("❌ Invalid date format. Use YYYY-MM-DD"))
            return

        self.stdout.write(f"⚡ Force running MLM Engine for {run_date}")

        # ✅ FORCE means: clear lock and re-run clean
        deleted = EngineLock.objects.filter(run_date=run_date).delete()[0]
        if deleted:
            self.stdout.write(self.style.WARNING(f"🗑️ Deleted existing EngineLock for {run_date}"))

        # 🔒 Create fresh lock (optional but nice for audit)
        EngineLock.objects.get_or_create(run_date=run_date)
        self.stdout.write(self.style.SUCCESS(f"🔒 EngineLock created for {run_date}"))

        # 🚀 Run engine (engine itself must handle duplicate-safe flags)
        try:
            run_full_daily_engine(run_date)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
            return

        self.stdout.write(self.style.SUCCESS(f"✅ FORCE Engine run completed safely for {run_date}"))

