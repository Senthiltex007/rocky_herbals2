# herbalapp/mlm/filters.py

from herbalapp.models import DailyIncomeReport, Member
from decimal import Decimal

ROOT_ID = "rocky001"

def get_valid_sponsor_children(run_date):
    """
    Returns list of members eligible for sponsor income today

    FINAL RULES (HARD DUPLICATE SAFE):
    1️⃣ Member must earn binary or eligibility income TODAY
    2️⃣ Member must be JOINED TODAY
    3️⃣ Sponsor must exist, active, binary eligible (lifetime)
    4️⃣ ROOT (rocky001) skipped
    5️⃣ If sponsor income already credited → BLOCK
    6️⃣ sponsor_today_processed=True → BLOCK
    """

    eligible_children = []

    # 🔒 HARD FILTER — duplicates impossible
    reports = DailyIncomeReport.objects.filter(
        date=run_date,
        member__joined_date=run_date,      # ONLY today joined
        sponsor_today_processed=False,     # not processed
        sponsor_income=Decimal("0.00")     # ✅ already credited → BLOCK
    )

    for report in reports:
        member = report.member

        # Skip ROOT
        if member.auto_id == ROOT_ID:
            continue

        # Must earn binary / eligibility income today
        if (report.binary_income + report.binary_eligibility_income) <= 0:
            continue

        sponsor = member.sponsor

        # Sponsor validation
        if (
            not sponsor or
            not sponsor.is_active or
            sponsor.auto_id == ROOT_ID or
            not sponsor.binary_eligible
        ):
            continue

        eligible_children.append(member)

    return eligible_children

