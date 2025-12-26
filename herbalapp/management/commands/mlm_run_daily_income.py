# herbalapp/management/commands/mlm_run_daily_income.py

from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime

from herbalapp.models import Member
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day


def get_today_joins_for_member(member, date):
    """
    TEMP TEST MODE:
    Force 1 join on both sides so we can test incomes.
    Later you will replace this with real BV/payment logic.
    """
    return 1, 1


class Command(BaseCommand):
    help = "Run daily binary + sponsor income for all members"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Date in YYYY-MM-DD (optional, default = today)",
        )

    def handle(self, *args, **options):
        # 1. Resolve date
        if options["date"]:
            run_date = timezone.datetime.fromisoformat(options["date"]).date()
        else:
            run_date = timezone.now().date()

        self.stdout.write(self.style.SUCCESS(f"▶ Running MLM incomes for date: {run_date}"))

        # 2. Loop all members
        for member in Member.objects.all().order_by("id"):

            left_joins_today, right_joins_today = get_today_joins_for_member(member, run_date)

            # Skip if no joins today
            if left_joins_today == 0 and right_joins_today == 0:
                continue

            # Direct call to final engine
            result = calculate_member_binary_income_for_day(
                left_joins_today=left_joins_today,
                right_joins_today=right_joins_today,
                left_cf_before=0,
                right_cf_before=0,
                binary_eligible=member.binary_eligible,
                member=member,
                run_date=run_date
            )

            self.stdout.write(
                f"Member {member.member_id} → "
                f"bin_pairs={result['binary_pairs']} | "
                f"bin_income={result['binary_income']} | "
                f"elig={result['eligibility_income']} | "
                f"sponsor_income={result['child_total_for_sponsor']}"
            )

        self.stdout.write(self.style.SUCCESS("✅ MLM daily income run completed."))

