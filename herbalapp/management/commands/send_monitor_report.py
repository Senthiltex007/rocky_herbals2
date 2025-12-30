# herbalapp/management/commands/send_monitor_report.py

from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime

from herbalapp.models import Member
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day


class Command(BaseCommand):
    help = "Run monitoring checks for all members (binary, sponsor, flashout, salary rules)"

    def handle(self, *args, **options):
        self.stdout.write("✅ Starting daily monitor report...")

        run_date = timezone.now().date()
        processed_members = 0
        total_binary_income = 0
        total_sponsor_income = 0

        # Loop through all members and run engine
        for member in Member.objects.all().order_by("id"):
            result = calculate_member_binary_income_for_day(
                left_joins_today=0,
                right_joins_today=0,
                left_cf_before=0,
                right_cf_before=0,
                binary_eligible=member.binary_eligible,
                member=member,
                run_date=run_date
            )
            processed_members += 1
            total_binary_income += result["binary_income"]
            total_sponsor_income += result["child_total_for_sponsor"]

        summary = {
            "processed_members": processed_members,
            "total_binary_income": total_binary_income,
            "total_sponsor_income": total_sponsor_income,
        }

        self.stdout.write(
            f"✅ Monitor report completed: {summary['processed_members']} members processed | "
            f"Binary={summary['total_binary_income']} | Sponsor={summary['total_sponsor_income']}"
        )

