from datetime import date, datetime
from django.core.management.base import BaseCommand
from herbalapp.models import Member
from herbalapp.engine.run import process_member_daily
from herbalapp.audit_full_income import run_full_income_audit


class Command(BaseCommand):
    help = "Run daily MLM engine for all root members + audit incomes"

    # ✅ Add --date argument
    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Run engine for a specific date (format: YYYY-MM-DD). Default: today',
        )

    def handle(self, *args, **options):
        date_str = options.get('date')
        if date_str:
            try:
                run_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                self.stdout.write(self.style.ERROR(f"❌ Invalid date format: {date_str}. Use YYYY-MM-DD"))
                return
        else:
            run_date = date.today()

        self.stdout.write(self.style.NOTICE(f"🚀 Starting daily engine run for {run_date}"))

        for root in Member.objects.filter(placement__isnull=True):
            try:
                process_member_daily(root, run_date)
                self.stdout.write(self.style.SUCCESS(f"✅ Engine run for root {root.auto_id}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"⚠️ Engine failed for {root.auto_id}: {e}"))

        self.stdout.write(self.style.NOTICE("🔍 Running full income audit..."))
        run_full_income_audit()

        self.stdout.write(self.style.SUCCESS("🎯 Daily engine + audit completed."))

