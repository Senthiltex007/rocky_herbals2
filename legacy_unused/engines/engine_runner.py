# herbalapp/engines/engine_runner.py
# Central runner to trigger sponsor, unlock, and daily binary logic

from django.db import transaction
from django.utils import timezone
from herbalapp.models import Member
from herbalapp.engines.sponsor_logic import credit_sponsor_income_for_join
from herbalapp.engines.binary_unlock import process_unlock_day
from herbalapp.engines.binary_daily import process_daily_binary

@transaction.atomic
def process_member_join(child: Member, placement: Member, sponsor: Member, fresh_pairs_today: int, run_date=None):
    """
    Called when a new member joins.
    - Handles unlock day for placement
    - Credits sponsor income
    - Processes daily binary income
    """
    if run_date is None:
        run_date = timezone.now().date()

    # Unlock day check
    if hasattr(placement, "is_unlock_condition_met") and placement.is_unlock_condition_met():
        process_unlock_day(placement, run_date=run_date)

    # Sponsor income
    sponsor_result = credit_sponsor_income_for_join(child, placement, sponsor, run_date=run_date)

    # Daily binary
    binary_result = process_daily_binary(placement, fresh_pairs_today, run_date=run_date)

    return {
        "sponsor_result": sponsor_result,
        "binary_result": binary_result,
    }

