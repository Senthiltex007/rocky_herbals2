from django.core.management.base import BaseCommand
from django.utils import timezone

from herbalapp.models import Member
from herbalapp.mlm_sponsor_runner import run_daily_binary_and_sponsor


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

            result = run_daily_binary_and_sponsor(
                member,
                left_joins_today=left_joins_today,
                right_joins_today=right_joins_today,
            )

            self.stdout.write(
                f"Member {member.member_id} → "
                f"bin_pairs={result['child_result']['binary_pairs']} | "
                f"bin_income={result['child_result']['binary_income']} | "
                f"elig={result['child_result']['eligibility_income']} | "
                f"sponsor_income={result['sponsor_income']}"
            )

        self.stdout.write(self.style.SUCCESS("✅ MLM daily income run completed."))

