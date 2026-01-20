# ==========================================================
# herbalapp/management/commands/mlm_run_daily.py
# ==========================================================

from django.core.management.base import BaseCommand
from django.utils import timezone

from herbalapp.models import Member
from herbalapp.mlm.core_pair_engine import run_core_pair_engine
from herbalapp.mlm.sponsor_engine import run_sponsor_engine


class Command(BaseCommand):
    help = "Run DAILY MLM engines (Core Pair + Sponsor)"

    def handle(self, *args, **options):
        today = timezone.localdate()

        self.stdout.write("🚀 MLM DAILY RUN STARTED")

        # -------------------------------
        # CORE PAIR ENGINE
        # -------------------------------
        members = Member.objects.exclude(auto_id="rocky004").order_by("auto_id")

        for member in members:
            run_core_pair_engine(member, today=today)
            self.stdout.write(
                f"✅ Core Pair processed: {member.auto_id} | "
                f"Binary Eligible: {member.binary_eligible} | "
                f"Left CF: {member.left_carry_forward} | Right CF: {member.right_carry_forward}"
            )

        self.stdout.write("✅ Core Pair Engine completed")

        # -------------------------------
        # SPONSOR ENGINE
        # -------------------------------
        for member in members:
            run_sponsor_engine(member, today=today)
            self.stdout.write(f"💰 Sponsor Engine run for: {member.auto_id}")

        self.stdout.write("✅ Sponsor Engine completed")
        self.stdout.write("🎉 MLM DAILY RUN FINISHED")

