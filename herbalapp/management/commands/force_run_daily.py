# herbalapp/management/commands/force_run_daily.py

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from datetime import date
from django.db import transaction

from herbalapp.models import EngineLock
from herbalapp.mlm.final_master_engine import run_full_daily_engine

class Command(BaseCommand):
    help = "FORCE RUN MLM Engine safely for a specific date (NO duplicate sponsor income)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Date to run engine (YYYY-MM-DD)"
        )

    def handle(self, *args, **options):
        # ✅ Set run_date
        run_date = parse_date(options["date"]) if options.get("date") else date.today()
        self.stdout.write(f"⚡ Force running MLM Engine for {run_date}")

        # 🔒 SAFE ENGINE LOCK
        lock, created = EngineLock.objects.get_or_create(run_date=run_date)
        if created:
            self.stdout.write(self.style.SUCCESS(f"🔒 EngineLock created for {run_date}"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️ EngineLock already exists for {run_date}"))

        # 🚀 Run engine always (idempotent & duplicate-safe)
        try:
            run_full_daily_engine(run_date)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
            return

        self.stdout.write(self.style.SUCCESS(f"✅ FORCE Engine run completed safely for {run_date}"))

