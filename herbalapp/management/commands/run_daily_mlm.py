# herbalapp/management/commands/run_daily_mlm.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date

from herbalapp.models import Member
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day


class Command(BaseCommand):
    help = "Run Daily MLM Engine (binary + sponsor + flashout + washout)"

    def handle(self, *args, **kwargs):
        today_str = date.today().isoformat()
        run_date = timezone.datetime.fromisoformat(today_str).date()

        processed_members = 0
        total_binary_income = 0
        total_sponsor_income = 0
        flashout_units = 0
        washout_pairs = 0

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
            flashout_units += result["flashout_units"]
            washout_pairs += result["washed_pairs"]

        summary = {
            "date": run_date,
            "processed_members": processed_members,
            "total_binary_income": total_binary_income,
            "total_sponsor_income": total_sponsor_income,
            "flashout_units": flashout_units,
            "washout_pairs": washout_pairs,
        }

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Daily MLM Engine executed for {summary['date']} → "
                f"{summary['processed_members']} members processed | "
                f"Binary={summary['total_binary_income']} | "
                f"Sponsor={summary['total_sponsor_income']} | "
                f"Flashout={summary['flashout_units']} | Washout={summary['washout_pairs']}"
            )
        )

