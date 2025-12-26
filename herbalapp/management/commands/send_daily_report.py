from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import EmailMessage
from herbalapp.run_daily_engine import run_daily_engine
import openpyxl
from io import BytesIO

class Command(BaseCommand):
    help = "Generate daily income report and send to admin with Excel attachment"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        summary = run_daily_engine(today)

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

        self.stdout.write(self.style.SUCCESS("Daily report generated and mailed with Excel attachment"))

