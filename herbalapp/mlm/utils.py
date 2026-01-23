# ==========================================================
# herbalapp/mlm/utils.py
# MLM DAILY ENGINE HELPER (Binary + Sponsor + Eligibility)
# ==========================================================

from datetime import date
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from herbalapp.models import Member, DailyIncomeReport
from herbalapp.mlm_engine_binary_runner import run_binary_engine
from herbalapp.mlm.sponsor_engine import run_sponsor_engine

ROOT_ID = "rocky001"  # Only skip this member for income

# ----------------------------------------------------------
# FULL DAILY ENGINE
# ----------------------------------------------------------
@transaction.atomic
def run_daily_engine(run_date: date = None):
    """
    ✅ Run MLM daily engine (binary + sponsor + eligibility)
    🔹 Skip ROOT_ID (rocky001)
    🔹 Prevent duplicate counting
    🔹 Respect old rules: pair locking, carry forward, eligibility bonus
    """

    if run_date is None:
        run_date = timezone.localdate()

    # 1️⃣ Get all members except root
    members = Member.objects.exclude(auto_id=ROOT_ID).order_by("id")

    for member in members:
        # Create/get today's report
        report, _ = DailyIncomeReport.objects.get_or_create(
            member=member,
            date=run_date
        )

        # -----------------------------
        # 2️⃣ Binary + eligibility calculation
        # -----------------------------
        run_binary_engine(member, run_date)

        # -----------------------------
        # 3️⃣ Sponsor income calculation
        # -----------------------------
        run_sponsor_engine(member, run_date)

        # -----------------------------
        # 4️⃣ Total income update safely
        # -----------------------------
        report.refresh_from_db()
        report.total_income = (
            report.binary_income +
            report.binary_eligibility_income +
            report.sponsor_income +
            getattr(report, "flashout_wallet_income", Decimal("0"))
        )
        report.save(update_fields=["total_income"])

