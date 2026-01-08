# herbalapp/management/commands/mlm_run_daily_income.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from decimal import Decimal

from herbalapp.models import Member, DailyIncomeReport
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day
from herbalapp.sponsor_engine import calculate_sponsor_income_for_day

DUMMY_ROOT = "rocky004"


class Command(BaseCommand):
    help = "Run MLM Daily Income (Binary + Sponsor + Flashout) safely (no duplicates)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Run income for specific date (YYYY-MM-DD)",
        )

    @transaction.atomic
    def handle(self, *args, **options):

        # ================= DATE =================
        if options.get("date"):
            run_date = datetime.strptime(options["date"], "%Y-%m-%d").date()
        else:
            run_date = timezone.localdate()

        self.stdout.write(self.style.WARNING(f"▶ Running MLM income for {run_date}"))

        # ================= DAILY LOCK =================
        if DailyIncomeReport.objects.filter(date=run_date).exists():
            self.stdout.write(
                self.style.ERROR(f"❌ Income already generated for {run_date}. Aborting.")
            )
            return

        # ================= MEMBERS =================
        members = (
            Member.objects
            .filter(is_active=True)
            .exclude(auto_id=DUMMY_ROOT)
            .order_by("id")
        )

        processed = 0

        for member in members:

            # ================= SNAPSHOT =================
            left_cf_before = member.left_cf or 0
            right_cf_before = member.right_cf or 0
            left_today = member.left_new_today or 0
            right_today = member.right_new_today or 0
            already_binary_eligible = member.binary_eligible

            # ================= BINARY ENGINE =================
            binary_result = calculate_member_binary_income_for_day(
                left_joins_today=left_today,
                right_joins_today=right_today,
                left_cf_before=left_cf_before,
                right_cf_before=right_cf_before,
                binary_eligible=already_binary_eligible,
            )

            # ================= ELIGIBILITY DAY CHECK =================
            eligibility_today = (
                binary_result.get("new_binary_eligible", False)
                and not already_binary_eligible
            )

            child_eligibility_income = Decimal("500") if eligibility_today else Decimal("0")

            # ================= UPDATE MEMBER =================
            member.left_cf = binary_result["left_cf_after"]
            member.right_cf = binary_result["right_cf_after"]

            if binary_result["new_binary_eligible"]:
                member.binary_eligible = True
                member.binary_eligible_date = run_date

            member.save(update_fields=[
                "left_cf",
                "right_cf",
                "binary_eligible",
                "binary_eligible_date",
            ])

            # ================= DAILY REPORT =================
            report = DailyIncomeReport.objects.create(
                member=member,
                date=run_date,
                binary_income=Decimal("0"),
                flashout_units=0,
                sponsor_income=Decimal("0"),
                total_income=Decimal("0"),
            )

            # ================= APPLY BINARY (STRICT RULE) =================
            # Eligibility day → NO binary, NO flashout
            if member.binary_eligible_date != run_date:
                report.binary_income = Decimal(binary_result.get("binary_income", 0))
                report.flashout_units = binary_result.get("flashout_units", 0)

            # ================= TOTAL BEFORE SPONSOR =================
            report.total_income = report.binary_income

            # ================= SPONSOR INCOME =================
            sponsor_income = calculate_sponsor_income_for_day(
                child_member=member,
                run_date=run_date,
                child_eligibility_income=child_eligibility_income,
                child_binary_income=report.binary_income,
            )
            sponsor_income = Decimal(sponsor_income or 0)

            report.sponsor_income = sponsor_income
            report.total_income += sponsor_income
            report.save(update_fields=["sponsor_income", "total_income"])

            processed += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"{member.auto_id} | "
                    f"Binary: {report.binary_income} | "
                    f"Sponsor: {report.sponsor_income} | "
                    f"Flashout: {report.flashout_units} | "
                    f"Total: {report.total_income}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ MLM DAILY INCOME COMPLETED | Date: {run_date} | Members: {processed}"
            )
        )

