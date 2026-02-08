# herbalapp/stockpoint/engine.py
from __future__ import annotations

from datetime import date as date_cls
from decimal import Decimal
from typing import Tuple

from django.db import transaction
from django.utils import timezone

from herbalapp.models import Member, Order, Commission
from herbalapp.stockpoint.utils import (
    find_nearest_stockpoint_upline_parent_chain,
    get_commission_percent,
)

# ------------------------------------------------------------
# IMPORTANT:
# Duplicate prevention needs a log table.
# For now we will create Commission rows, but it can double-pay on rerun.
# So we WILL implement a log model in the next step (recommended).
# ------------------------------------------------------------


def run_stockpoint_for_date(run_date: date_cls) -> Tuple[int, int]:
    """
    Process all PAID orders for a given date and generate stockpoint commissions.

    Returns:
        (processed_orders_count, created_commissions_count)
    """
    orders = Order.objects.filter(status="Paid", created_at__date=run_date).select_related("member", "product")
    processed = 0
    created = 0

    for order in orders:
        processed += 1
        created += int(process_single_order(order))

    return processed, created


def process_single_order(order: Order) -> bool:
    """
    Process a single order:
    - find receiver (nearest upline with stockpoint level)
    - compute commission
    - create Commission record
    - credit receiver wallet (optional)

    Returns:
        True if commission created else False
    """
    buyer = order.member
    receiver = find_nearest_stockpoint_upline_parent_chain(buyer)

    if not receiver:
        return False

    percent = get_commission_percent(receiver)
    if percent <= 0:
        return False

    base_amount = Decimal(order.total_amount or 0)
    if base_amount <= 0:
        return False

    commission_amount = (base_amount * percent).quantize(Decimal("0.01"))

    with transaction.atomic():
        # Create Commission row
        Commission.objects.create(
            member=receiver,
            payment_id=None,  # keep null if not using Payment; adjust if needed
            commission_type=str(receiver.level),
            percentage=(percent * Decimal("100")).quantize(Decimal("0.01")),
            commission_amount=commission_amount,
        )

        # Optional: credit receiver main_wallet
        receiver.main_wallet = (receiver.main_wallet or Decimal("0.00")) + commission_amount
        receiver.save(update_fields=["main_wallet"])

    return True

