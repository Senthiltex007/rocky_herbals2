# ==========================================================
# herbalapp/mlm/sponsor_engine.py
# ==========================================================
from decimal import Decimal
from herbalapp.models import Member

ROOT_ID = "rocky001"


# ----------------------------------------------------------
# Check if a member is binary eligible (1:1 pair)
# ----------------------------------------------------------
def is_sponsor_binary_eligible(member: Member) -> bool:
    """
    Sponsor eligibility rule: must have at least one member on each leg
    """
    left = member.left_child()
    right = member.right_child()
    return bool(left and right)


# ----------------------------------------------------------
# Determine the correct sponsor receiver for a child
# ----------------------------------------------------------
def get_sponsor_receiver(child: Member):
    """
    Decide which member should receive sponsor income for this child
    RULES:
    1️⃣ If placement == sponsor → parent of placement receives
    2️⃣ If placement != sponsor → sponsor directly receives
    3️⃣ Must satisfy binary eligibility (1:1)
    Returns: Member instance or None
    """
    if not child.sponsor or child.sponsor.auto_id == ROOT_ID:
        return None

    # Rule 1: self-sponsor case → placement.parent
    if child.placement_id == child.sponsor_id:
        parent = child.placement.parent if child.placement else None
        if parent and parent.auto_id != ROOT_ID:
            return parent
        return None

    # Rule 2: normal sponsor
    return child.sponsor


# ----------------------------------------------------------
# Calculate sponsor amount helper (does NOT credit)
# ----------------------------------------------------------
def calculate_sponsor_amount(child_report):
    """
    Sponsor income for this child = child's binary + eligibility income
    Flashout is NOT included.
    Returns Decimal amount (to be credited by main engine)
    """
    return (
        (child_report.binary_income or Decimal("0")) +
        (child_report.binary_eligibility_income or Decimal("0"))
    )

# ==========================================================
# Note:
# - This script no longer credits sponsor_income anywhere.
# - Use only for helper calculations inside main engine.
# ==========================================================

