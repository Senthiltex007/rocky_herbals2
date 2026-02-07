# herbalapp/mlm/filters.py

from decimal import Decimal
from django.db.models import Q
from herbalapp.models import DailyIncomeReport


def get_valid_sponsor_children(run_date):
    """
    Returns list of members eligible for sponsor income today

    FINAL RULES (DUPLICATE SAFE):
    1️⃣ Child must earn (binary_income > 0 OR binary_eligibility_income > 0) TODAY
    2️⃣ sponsor_today_processed=False (daily lock)
    """

    reports = DailyIncomeReport.objects.filter(
        date=run_date,
        sponsor_today_processed=False
    ).filter(
        Q(binary_income__gt=Decimal("0.00")) |
        Q(binary_eligibility_income__gt=Decimal("0.00"))
    )

    return [r.member for r in reports]

