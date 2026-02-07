# herbalapp/management/commands/mlm_reset_all.py

from django.core.management.base import BaseCommand
from decimal import Decimal
from herbalapp.models import Member, DailyIncomeReport, EngineLock

ROOT_ID = "rocky001"


class Command(BaseCommand):
    help = "RESET all MLM incomes, eligibility, and engine locks (SAFE RESET)"

    def handle(self, *args, **options):
        self.stdout.write("⚠️ RESETTING ALL MLM DATA...")

        # -----------------------------
        # 1️⃣ Reset DailyIncomeReport
        # -----------------------------
        reports = DailyIncomeReport.objects.all()

        for report in reports:
            # incomes
            report.binary_income = Decimal("0.00")
            report.binary_eligibility_income = Decimal("0.00")
            report.eligibility_income = Decimal("0.00")  # ✅ IMPORTANT
            report.sponsor_income = Decimal("0.00")
            report.flashout_wallet_income = Decimal("0.00")
            report.total_income = Decimal("0.00")

            # carry forward
            report.left_cf = 0
            report.right_cf = 0

            # flags
            report.sponsor_processed = False
            report.sponsor_today_processed = False
            report.earned_fresh_binary_today = False
            report.total_income_locked = False
            report.binary_income_processed = False  # ✅ MAIN FIX (prevents "already processed today")

            report.save()

        self.stdout.write(f"✅ Reset {reports.count()} income reports")

        # -----------------------------
        # 2️⃣ Reset Member Eligibility
        # -----------------------------
        members = Member.objects.exclude(auto_id=ROOT_ID)

        for member in members:
            member.binary_eligible = False
            member.save(update_fields=["binary_eligible"])

        self.stdout.write(f"✅ Reset eligibility for {members.count()} members")

        # -----------------------------
        # 3️⃣ CLEAR EngineLock (VERY IMPORTANT)
        # -----------------------------
        lock_count = EngineLock.objects.count()
        EngineLock.objects.all().delete()
        self.stdout.write(f"🔓 Cleared {lock_count} EngineLocks")

        self.stdout.write(self.style.SUCCESS("🎯 MLM RESET COMPLETED SUCCESSFULLY"))

