# herbalapp/management/commands/send_daily_report.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import EmailMessage
import openpyxl
from io import BytesIO

from herbalapp.models import Member
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day


class Command(BaseCommand):
    help = "Generate daily income report and send to admin with Excel attachment"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
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
                run_date=today
            )
            processed_members += 1
            total_binary_income += result["binary_income"]
            total_sponsor_income += result["child_total_for_sponsor"]
            flashout_units += result["flashout_units"]
            washout_pairs += result["washed_pairs"]

        summary = {
            "date": today,
            "processed_members": processed_members,
            "total_binary_income": total_binary_income,
            "total_sponsor_income": total_sponsor_income,
            "flashout_units": flashout_units,
            "washout_pairs": washout_pairs,
        }

        # Create Excel workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Daily Income Report"

        ws.append([
            "Date", "Processed Members", "Total Binary Income",
            "Total Sponsor Income", "Flashout Units", "Washout Pairs"
        ])
        ws.append([
            summary["date"],
            summary["processed_members"],
            summary["total_binary_income"],
            summary["total_sponsor_income"],
            summary["flashout_units"],
            summary["washout_pairs"],
        ])

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # Send email with Excel attachment
        email = EmailMessage(
            subject=f"Rocky Herbals Daily Income Report - {today}",
            body="Please find attached the daily income summary report.",
            from_email="rockysriherbals@gmail.com",
            to=["rockysriherbals@gmail.com"],
        )
        email.attach(
            f"daily_income_{today}.xlsx",
            output.read(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        email.send()

        self.stdout.write(self.style.SUCCESS("✅ Daily report generated and mailed with Excel attachment"))

