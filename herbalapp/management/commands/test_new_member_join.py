# ==========================================================
# herbalapp/management/commands/test_new_member_join.py
# Test Async MLM Engine Trigger on New Member Join
# ==========================================================
from django.core.management.base import BaseCommand
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport

import time

ROOT_ID = "rocky001"

class Command(BaseCommand):
    help = "Test Async Daily Engine Trigger when a new member joins"

    def handle(self, *args, **options):
        run_date = timezone.localdate()
        self.stdout.write(f"🚀 Simulating new member join on {run_date}")

        # Create a test member (ensure it's not ROOT)
        test_member_id = "testmember001"
        member, created = Member.objects.get_or_create(
            member_id=test_member_id,
            defaults={
                "name": "Test Member",
                "auto_id": test_member_id,
                "binary_eligible": False,
                "sponsor_id": ROOT_ID,   # can assign ROOT as sponsor for test
                "placement_id": ROOT_ID,
                "main_wallet": 0,
                "sponsor_income": 0,
            }
        )

        if created:
            self.stdout.write(f"✅ New member {member.member_id} created. Async engine should trigger.")

            # Wait a few seconds for the async thread to finish
            time.sleep(5)

            # Check daily income report
            try:
                report = DailyIncomeReport.objects.get(member=member, date=run_date)
                self.stdout.write(
                    f"Member {member.member_id} income report: "
                    f"Binary={report.binary_income}, "
                    f"Eligibility={report.binary_eligibility_income}, "
                    f"Sponsor={report.sponsor_income}, "
                    f"Total={report.total_income}"
                )
            except DailyIncomeReport.DoesNotExist:
                self.stdout.write("❌ DailyIncomeReport not created by async engine!")

        else:
            self.stdout.write(f"⚠ Member {member.member_id} already exists. Delete before testing again.")

