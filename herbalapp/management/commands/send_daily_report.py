from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import EmailMessage
from herbalapp.models import Member, DailyIncomeReport
import openpyxl
from io import BytesIO

class Command(BaseCommand):
    help = "Generate daily income report and send to admin with Excel attachment"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        reports = []
        for member in Member.objects.all():
            income = member.calculate_full_income()
            report = DailyIncomeReport.objects.create(
                date=today,
                member=member,
                binary_income=income["binary_income"],
                flash_bonus=income["flash_bonus"],
                sponsor_income=income["sponsor_income"],
                salary=income["salary"],
                stock_commission=income["stock_commission"],
                total_income=income["total_income_all"],
            )
            reports.append(report)

        # Create Excel workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Daily Income Report"

        # Header
        ws.append([
            "Member ID", "Name", "Joining Package",
            "Binary Income", "Flash Bonus", "Sponsor Income",
            "Salary", "Stock Commission", "Total Income"
        ])

        # Data rows
        for r in reports:
            ws.append([
                r.member.auto_id,
                r.member.name,
                r.member.package,
                r.binary_income,
                r.flash_bonus,
                r.sponsor_income,
                r.salary,
                r.stock_commission,
                r.total_income,
            ])

        # Save to memory
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # Prepare mail
        email = EmailMessage(
            subject=f"Rocky Herbals Daily Income Report - {today}",
            body="Please find attached the daily income report.",
            from_email="rockysriherbals@gmail.com",
            to=["rockysriherbals@gmail.com"],
        )
        email.attach(f"daily_income_{today}.xlsx", output.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        email.send()

        self.stdout.write(self.style.SUCCESS("Daily report generated and mailed with Excel attachment"))

