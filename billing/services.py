# billing/services.py
from __future__ import annotations

from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from billing.models import (
    PurchaseInvoice, PurchaseItem,
    SalesInvoice, SalesItem,
    SalesReturn, SalesReturnItem,
    StockLedger
)


def _safe_int(v) -> int:
    try:
        return int(v)
    except Exception:
        return 0


# ============================================================
# PURCHASE → STOCK IN
# ============================================================
def receive_purchase(purchase_id: int) -> str:
    """
    Mark purchase as received and add stock IN to ledger.
    Duplicate-safe: If already received, does nothing.
    """
    with transaction.atomic():
        purchase = PurchaseInvoice.objects.select_for_update().get(id=purchase_id)

        if purchase.status == "received":
            return f"✅ Purchase {purchase.purchase_no} already received."

        items = list(purchase.items.select_related("product").all())
        if not items:
            return "⛔ Purchase has no items."

        # Calculate totals and save items
        subtotal = Decimal("0.00")
        gst_total = Decimal("0.00")
        grand_total = Decimal("0.00")

        for it in items:
            it.calculate()
            it.save(update_fields=["line_subtotal", "line_gst", "line_total"])
            subtotal += it.line_subtotal
            gst_total += it.line_gst
            grand_total += it.line_total

        purchase.subtotal = subtotal
        purchase.gst_total = gst_total
        purchase.grand_total = grand_total

        # Stock IN entries
        for it in items:
            StockLedger.apply_movement(
                product_id=it.product_id,
                ref_type="purchase",
                ref_id=purchase.id,
                qty_in=_safe_int(it.qty),
                qty_out=0
            )

        purchase.status = "received"
        purchase.received_at = timezone.now()
        purchase.save(update_fields=["subtotal", "gst_total", "grand_total", "status", "received_at"])

        return f"✅ Purchase {purchase.purchase_no} received + stock updated."


# ============================================================
# SALES → STOCK OUT (only when invoice becomes PAID)
# ============================================================
def finalize_invoice_totals(invoice: SalesInvoice) -> None:
    """
    Recalculate invoice totals from items + payments.
    """
    for it in invoice.items.all():
        it.calculate()
        it.save(update_fields=["discount_amount", "line_subtotal", "gst_amount", "line_total"])
    invoice.recalc_totals()
    invoice.save(update_fields=[
        "subtotal", "discount_total", "gst_total", "grand_total",
        "paid_total", "due_total", "status", "paid_at"
    ])


def apply_stock_out_for_paid_invoice(invoice_id: int) -> str:
    """
    When invoice is PAID, apply stock OUT once.
    Duplicate-safe: checks existing StockLedger entries for this invoice.
    """
    with transaction.atomic():
        invoice = SalesInvoice.objects.select_for_update().get(id=invoice_id)

        if invoice.status != "paid":
            return f"⛔ Invoice {invoice.invoice_no} is not PAID (current: {invoice.status})."

        # Duplicate protection: if stock already deducted for this invoice, skip
        already = StockLedger.objects.filter(ref_type="sale", ref_id=invoice.id).exists()
        if already:
            return f"✅ Stock OUT already applied for {invoice.invoice_no}."

        items = list(invoice.items.select_related("product").all())
        if not items:
            return f"⛔ Invoice {invoice.invoice_no} has no items."

        # Check stock availability BEFORE deduct
        for it in items:
            current = StockLedger.current_balance(it.product_id)
            if current < _safe_int(it.qty):
                return f"⛔ Low stock for {it.product.name}. Available={current}, Required={it.qty}"

        # Apply stock OUT
        for it in items:
            StockLedger.apply_movement(
                product_id=it.product_id,
                ref_type="sale",
                ref_id=invoice.id,
                qty_in=0,
                qty_out=_safe_int(it.qty),
            )

        return f"✅ Stock OUT applied for PAID invoice {invoice.invoice_no}."


# ============================================================
# SALES RETURN → STOCK IN
# ============================================================
def apply_sales_return(return_id: int) -> str:
    """
    Sales return increases stock back.
    Duplicate-safe: checks existing ledger entries for this return.
    """
    with transaction.atomic():
        ret = SalesReturn.objects.select_for_update().get(id=return_id)

        already = StockLedger.objects.filter(ref_type="sale_return", ref_id=ret.id).exists()
        if already:
            return f"✅ Return stock already applied for {ret.invoice.invoice_no}"

        items = list(ret.items.select_related("product").all())
        if not items:
            return "⛔ Return has no items."

        for it in items:
            StockLedger.apply_movement(
                product_id=it.product_id,
                ref_type="sale_return",
                ref_id=ret.id,
                qty_in=_safe_int(it.qty),
                qty_out=0,
            )

        return f"✅ Stock IN applied for return of {ret.invoice.invoice_no}"

