from datetime import datetime
from django.core.management.base import BaseCommand
from herbalapp.models import Member
from herbalapp.engine.run import process_member_daily
from herbalapp.audit_full_income import run_full_income_audit

class Command(BaseCommand):
    help = "Reset MLM members (keep selected) and run daily engine for a given date"

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Run engine for a specific date (YYYY-MM-DD). Default: today',
        )
        parser.add_argument(
            '--keep',
            type=str,
            help='Comma-separated auto_ids to keep (e.g., "rocky004,rocky005")',
            required=True
        )

    def handle(self, *args, **options):
        # -----------------------
        # Parse date
        # -----------------------
        date_str = options.get('date')
        if date_str:
            try:
                run_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                self.stdout.write(self.style.ERROR(f"❌ Invalid date format: {date_str}. Use YYYY-MM-DD"))
                return
        else:
            run_date = datetime.today().date()

        # -----------------------
        # Parse keep list
        # -----------------------
        keep_str = options.get('keep')
        keep_ids = [s.strip() for s in keep_str.split(',') if s.strip()]
        if not keep_ids:
            self.stdout.write(self.style.ERROR("❌ You must provide at least one auto_id to keep."))
            return

        # -----------------------
        # Delete all other members
        # -----------------------
        deleted_count, related = Member.objects.exclude(auto_id__in=keep_ids).delete()
        self.stdout.write(self.style.NOTICE(f"🗑️ Deleted {deleted_count} members not in {keep_ids}"))

        # -----------------------
        # Run daily engine for remaining roots
        # -----------------------
        self.stdout.write(self.style.NOTICE(f"🚀 Running daily engine for {run_date}"))

        roots = Member.objects.filter(auto_id__in=keep_ids)
        for root in roots:
            try:
                process_member_daily(root, run_date)
                self.stdout.write(self.style.SUCCESS(f"✅ Engine run for root {root.auto_id}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"⚠️ Engine failed for root {root.auto_id}: {e}"))

        # -----------------------
        # Run full income audit
        # -----------------------
        self.stdout.write(self.style.NOTICE("🔍 Running full income audit..."))
        run_full_income_audit()

        self.stdout.write(self.style.SUCCESS("🎯 Reset + daily engine + audit completed."))

