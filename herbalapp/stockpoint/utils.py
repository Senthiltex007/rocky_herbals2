# herbalapp/stockpoint/utils.py
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from herbalapp.models import Member

COMMISSION_PERCENT = {
    "district": Decimal("0.07"),
    "taluk": Decimal("0.05"),
    "pincode": Decimal("0.03"),
}


def find_nearest_stockpoint_upline_parent_chain(member: Member) -> Optional[Member]:
    """
    Find nearest upline (parent chain) who has a stockpoint level:
        district / taluk / pincode

    Returns:
        Member or None
    """
    cur = member.parent
    while cur:
        lvl = getattr(cur, "level", None)
        if lvl in COMMISSION_PERCENT:
            # Optional: only active
            if hasattr(cur, "is_active") and not cur.is_active:
                cur = cur.parent
                continue
            return cur
        cur = cur.parent
    return None


def get_commission_percent(receiver: Member) -> Decimal:
    lvl = getattr(receiver, "level", None)
    return COMMISSION_PERCENT.get(lvl, Decimal("0.00"))

