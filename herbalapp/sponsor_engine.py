# herbalapp/sponsor_engine.py

from decimal import Decimal
from herbalapp.models import Member


def calculate_sponsor_income_for_day(
    *,
    child_member: Member,
    run_date,
    child_eligibility_income: int | float,
    child_binary_income: int | float,
):
    """
    SPONSOR INCOME – EXACT BUSINESS RULES

    Rule-1:
        placement_id == sponsor_id
        -> sponsor income goes to PLACEMENT PARENT

    Rule-2:
        placement_id != sponsor_id
        -> sponsor income goes to SPONSOR ID

    Rule-3 (MANDATORY):
        Receiver MUST be binary eligible

    Amount:
        child_eligibility_income + child_binary_income

    NOT INCLUDED:
        flashout, washout
    """

    # -----------------------------
    # BASIC VALIDATION
    # -----------------------------
    if not child_member:
        return Decimal("0")

    total_child_income = (
        Decimal(child_eligibility_income or 0)
        + Decimal(child_binary_income or 0)
    )

    if total_child_income <= 0:
        return Decimal("0")

    placement_id = child_member.placement_id
    sponsor_id = child_member.sponsor_id

    sponsor_target = None

    # -----------------------------
    # RULE-1: placement == sponsor
    # -----------------------------
    if placement_id and sponsor_id and placement_id == sponsor_id:
        sponsor_target = child_member.parent

    # -----------------------------
    # RULE-2: placement != sponsor
    # -----------------------------
    elif sponsor_id:
        sponsor_target = Member.objects.filter(
            auto_id=sponsor_id
        ).first()

    # No valid sponsor
    if not sponsor_target:
        return Decimal("0")

    # Skip dummy root
    if sponsor_target.auto_id == "rocky004":
        return Decimal("0")

    # -----------------------------
    # RULE-3: sponsor must be eligible
    # -----------------------------
    if not sponsor_target.binary_eligible:
        return Decimal("0")

    return total_child_income

