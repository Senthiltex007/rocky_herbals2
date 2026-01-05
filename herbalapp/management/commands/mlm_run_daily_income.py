# herbalapp/management/commands/mlm_run_daily_income.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day

def get_previous_carry_forward(member, run_date):
    prev = (
        DailyIncomeReport.objects
        .filter(member=member, date__lt=run_date)
        .order_by("-date")
        .first()
    )
    if not prev:
        return 0, 0
    return prev.left_cf_after, prev.right_cf_after

def get_today_joins_for_member(member, date):
    """
    TEMP TEST MODE
    """
    # Ideally, count members added under left/right today
    return 1, 1

def calculate_sponsor_income(member, binary_income, eligibility_income):
    """
    Sponsor income calculation as per rules:
    1️⃣ Placement ID = Sponsor ID → placement's parent gets sponsor income
    2️⃣ Placement ID != Sponsor ID → sponsor gets sponsor income
    3️⃣ Sponsor must have completed 1:1 pair to receive income
    """
    sponsor_income = 0
    sponsor_member = None

    if member.placement_id and member.sponsor_id:
        if member.placement_id == member.sponsor_id:
            # Rule 1: sponsor income goes to placement parent
            sponsor_member = Member.objects.filter(id=member.placement_id).first()
        else:
            # Rule 2: sponsor income goes to sponsor
            sponsor_member = Member.objects.filter(id=member.sponsor_id).first()

    if sponsor_member:
        # Rule 3: check if sponsor has at least 1:1 pair completed
        left = sponsor_member.left_child_count if hasattr(sponsor_member, 'left_child_count') else 0
        right = sponsor_member.right_child_count if hasattr(sponsor_member, 'right_child_count') else 0
        if min(left, right) >= 1:
            sponsor_income = binary_income + eligibility_income
            sponsor_member.sponsor_income_today = getattr(sponsor_member, 'sponsor_income_today', 0) + sponsor_income
            sponsor_member.save()
    return sponsor_income

class Command(BaseCommand):
    help = "Run daily MLM binary & sponsor income"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="YYYY-MM-DD (default: today)",
        )

    def handle(self, *args, **options):
        run_date = (
            timezone.datetime.fromisoformat(options["date"]).date()
            if options.get("date")
            else timezone.now().date()
        )
        self.stdout.write(f"▶ Running MLM incomes for {run_date}")

        for member in Member.objects.all().order_by("id"):

            left_today, right_today = get_today_joins_for_member(member, run_date)
            left_cf_before, right_cf_before = get_previous_carry_forward(member, run_date)

            result = calculate_member_binary_income_for_day(
                left_joins_today=left_today,
                right_joins_today=right_today,
                left_cf_before=left_cf_before,
                right_cf_before=right_cf_before,
                binary_eligible=member.binary_eligible,
            )

            # Update eligibility
            if result["new_binary_eligible"] and not member.binary_eligible:
                member.binary_eligible = True

            # Update carry forward
            member.left_carry_forward = result["left_cf_after"]
            member.right_carry_forward = result["right_cf_after"]

            # Sponsor income
            sponsor_income = calculate_sponsor_income(
                member,
                binary_income=result["binary_income"],
                eligibility_income=result["eligibility_income"],
            )

            member.save()

            # Save daily report
            DailyIncomeReport.objects.update_or_create(
                member=member,
                date=run_date,
                defaults={
                    "left_joins": left_today,
                    "right_joins": right_today,
                    "left_cf_before": left_cf_before,
                    "right_cf_before": right_cf_before,
                    "left_cf_after": result["left_cf_after"],
                    "right_cf_after": result["right_cf_after"],
                    "eligibility_income": result["eligibility_income"],
                    "binary_income": result["binary_income"],
                    "sponsor_income": sponsor_income,
                    "flashout_units": result["flashout_units"],
                    "washed_pairs": result["washed_pairs"],
                    "total_income": result["total_income"] + sponsor_income,
                },
            )

            self.stdout.write(
                f"{member.auto_id} → "
                f"Binary ₹{result['binary_income']} | "
                f"Eligibility ₹{result['eligibility_income']} | "
                f"Sponsor ₹{sponsor_income} | "
                f"Flashout Units {result['flashout_units']} (product)"
            )

        self.stdout.write("✅ MLM daily income run completed")

