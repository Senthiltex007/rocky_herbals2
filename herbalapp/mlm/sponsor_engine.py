# herbalapp/mlm/sponsor_engine.py

from decimal import Decimal
from django.db import transaction
from herbalapp.models import DailyIncomeReport, Member
from herbalapp.mlm.filters import get_valid_sponsor_children

ROOT_ID = "rocky001"

@transaction.atomic
def run_sponsor_income_safe(run_date):
    """
    ✅ Safe Sponsor Income Engine
    Rules applied:
    1️⃣ If placement_id == sponsor_id → placement itself gets sponsor income (except ROOT)
    2️⃣ If placement_id != sponsor_id → sponsor gets sponsor income (except ROOT)
    3️⃣ Sponsor must have completed at least one 1:1 pair (binary_eligible=True)
    """
    print("🔄 Running Safe Sponsor Engine")

    children = get_valid_sponsor_children(run_date)

    for child in children:
        child_report, _ = DailyIncomeReport.objects.get_or_create(
            member=child,
            date=run_date
        )

        if child_report.sponsor_processed:
            continue

        receiver = None

        # Rule 1: placement == sponsor → placement itself
        if child.parent_id == child.sponsor_id:
            if child.parent and child.parent.auto_id != ROOT_ID:
                receiver = child.parent
        else:
            # Rule 2: placement != sponsor → sponsor
            if child.sponsor and child.sponsor.auto_id != ROOT_ID:
                receiver = child.sponsor

        # Rule 3: sponsor must be binary eligible
        if receiver and not receiver.binary_eligible:
            receiver = None

        sponsor_amount = child_report.binary_income + child_report.binary_eligibility_income

        if receiver and sponsor_amount > 0:
            receiver_report, _ = DailyIncomeReport.objects.get_or_create(
                member=receiver,
                date=run_date
            )
            receiver_report.sponsor_income += sponsor_amount
            receiver_report.total_income += sponsor_amount
            receiver_report.save(update_fields=["sponsor_income", "total_income"])

            child_report.sponsor_processed = True
            child_report.save(update_fields=["sponsor_processed"])

            print(f"✅ Sponsor income {sponsor_amount} credited to {receiver.auto_id}, child: {child.auto_id}")

    print("✅ Safe Sponsor Engine Completed")

