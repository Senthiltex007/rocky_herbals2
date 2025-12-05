from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from herbalapp.models import Member
import openpyxl
from io import BytesIO
from django.utils import timezone

class Command(BaseCommand):
    help = "Generate total income report (till date) and send to admin with Excel attachment"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Total Income Till Date"

        ws.append([
            "Member ID", "Name", "Joining Package",
            "Binary Income", "Flash Bonus", "Sponsor Income",
            "Salary", "Stock Commission", "Total Income"
        ])

        for m in Member.objects.all():
            income = m.calculate_full_income()
            ws.append([
                m.auto_id,
                m.name,
                m.package,
                income["binary_income"],
                income["flash_bonus"],
                income["sponsor_income"],
                income["salary"],
                income["stock_commission"],
                income["total_income_all"],
            ])

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        email = EmailMessage(
            subject=f"Rocky Herbals Total Income Report Till {today}",
            body="Please find attached the total income report till date.",
            from_email="rockysriherbals@gmail.com",
            to=["rockysriherbals@gmail.com"],
        )
        email.attach(f"total_income_till_{today}.xlsx", output.read(),
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        email.send()

        self.stdout.write(self.style.SUCCESS("Total income report generated and mailed with Excel attachment"))

