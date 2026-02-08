# billing/models.py
from __future__ import annotations

from decimal import Decimal
from django.db import models, transaction
from django.utils import timezone


# -----------------------------
# Helpers
# -----------------------------
def money(v) -> Decimal:
    return (Decimal(v or 0)).quantize(Decimal("0.01"))


# -----------------------------
# Parties
# -----------------------------
class Customer(models.Model):
    CUSTOMER_TYPES = [
        ("retail", "Retail / POS"),
        ("wholesale", "Wholesale"),
    ]

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, default="")

    # GST (usually wholesale)
    gstin = models.CharField(max_length=20, blank=True, default="")
    state_code = models.CharField(max_length=5, blank=True, default="TN")

    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES, default="retail")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.customer_type})"


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, default="")

    gstin = models.CharField(max_length=20, blank=True, default="")
    state_code = models.CharField(max_length=5, blank=True, default="TN")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


# -----------------------------
# Invoice Number Series
# -----------------------------
class InvoiceSeries(models.Model):
    """
    Keeps sequential invoice numbers per financial year.
    Example invoice_no: RH/2025-26/000123
    """
    key = models.CharField(max_length=50, unique=True)  # e.g. "SALES:2025-26", "PURCHASE:2025-26"
    last_number = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.key} -> {self.last_number}"

    @staticmethod
    def current_fin_year(today=None) -> str:
        today = today or timezone.localdate()
        year = today.year
        # India FY: Apr-Mar
        if today.month >= 4:
            start = year
            end = year + 1
        else:
            start = year - 1
            end = year
        return f"{start}-{str(end)[-2:]}"


def next_invoice_number(prefix: str, today=None) -> str:
    """
    prefix: "RH" (or your brand)
    returns: RH/2025-26/000001
    """
    today = today or timezone.localdate()
    fy = InvoiceSeries.current_fin_year(today=today)
    key = f"SALES:{fy}"

    with transaction.atomic():
        series, _ = InvoiceSeries.objects.select_for_update().get_or_create(key=key)
        series.last_number += 1
        series.save(update_fields=["last_number"])
        return f"{prefix}/{fy}/{series.last_number:06d}"


def next_purchase_number(prefix: str, today=None) -> str:
    today = today or timezone.localdate()
    fy = InvoiceSeries.current_fin_year(today=today)
    key = f"PURCHASE:{fy}"

    with transaction.atomic():
        series, _ = InvoiceSeries.objects.select_for_update().get_or_create(key=key)
        series.last_number += 1
        series.save(update_fields=["last_number"])
        return f"{prefix}-P/{fy}/{series.last_number:06d}"


# -----------------------------
# Purchase (Stock IN)
# -----------------------------
class PurchaseInvoice(models.Model):
    STATUS = [
        ("draft", "Draft"),
        ("received", "Received"),
        ("cancelled", "Cancelled"),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchases")
    purchase_no = models.CharField(max_length=50, unique=True, blank=True, default="")

    invoice_ref = models.CharField(max_length=100, blank=True, default="")  # supplier bill no
    invoice_date = models.DateField(default=timezone.localdate)

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    gst_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    status = models.CharField(max_length=20, choices=STATUS, default="draft")
    received_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-invoice_date", "-id"]

    def __str__(self) -> str:
        return f"{self.purchase_no or 'PURCHASE'} - {self.supplier.name}"

    def save(self, *args, **kwargs):
        if not self.purchase_no:
            self.purchase_no = next_purchase_number(prefix="RH")
        super().save(*args, **kwargs)


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name="items")

    # Use your existing Product model from herbalapp
    product = models.ForeignKey("herbalapp.Product", on_delete=models.PROTECT)

    qty = models.PositiveIntegerField(default=1)
    purchase_rate = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))  # cost
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))       # %

    line_subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    line_gst = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    line_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    def __str__(self) -> str:
        return f"{self.product.name} x {self.qty}"

    def calculate(self):
        sub = money(self.purchase_rate) * Decimal(int(self.qty))
        gst = (sub * money(self.gst_rate) / Decimal("100")).quantize(Decimal("0.01"))
        tot = sub + gst
        self.line_subtotal = sub
        self.line_gst = gst
        self.line_total = tot


# -----------------------------
# Sales Invoice (Stock OUT)
# -----------------------------
class SalesInvoice(models.Model):
    INVOICE_TYPES = [
        ("pos", "POS / Retail"),
        ("wholesale", "Wholesale"),
    ]
    STATUS = [
        ("draft", "Draft"),
        ("paid", "Paid"),
        ("partial", "Partial"),
        ("credit", "Credit / Due"),
        ("cancelled", "Cancelled"),
    ]

    invoice_no = models.CharField(max_length=50, unique=True, blank=True, default="")
    invoice_date = models.DateField(default=timezone.localdate)

    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPES, default="pos")
    status = models.CharField(max_length=20, choices=STATUS, default="draft")

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True, blank=True, related_name="invoices")
    customer_name = models.CharField(max_length=200, blank=True, default="")  # POS quick name
    customer_phone = models.CharField(max_length=20, blank=True, default="")

    # GST fields
    customer_gstin = models.CharField(max_length=20, blank=True, default="")
    place_of_supply_state = models.CharField(max_length=5, blank=True, default="TN")  # for IGST logic later

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    discount_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    gst_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    paid_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    due_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-invoice_date", "-id"]

    def __str__(self) -> str:
        return self.invoice_no or f"SALES #{self.id}"

    def save(self, *args, **kwargs):
        if not self.invoice_no:
            self.invoice_no = next_invoice_number(prefix="RH")
        super().save(*args, **kwargs)

    def recalc_totals(self):
        items = list(self.items.all())
        sub = sum((money(i.line_subtotal) for i in items), Decimal("0.00"))
        disc = sum((money(i.discount_amount) for i in items), Decimal("0.00"))
        gst = sum((money(i.gst_amount) for i in items), Decimal("0.00"))
        total = sum((money(i.line_total) for i in items), Decimal("0.00"))

        self.subtotal = money(sub)
        self.discount_total = money(disc)
        self.gst_total = money(gst)
        self.grand_total = money(total)

        # due based on payments
        self.paid_total = money(sum((money(p.amount) for p in self.payments.all()), Decimal("0.00")))
        self.due_total = money(self.grand_total - self.paid_total)

        # ✅ AUTO STATUS UPDATE (even from draft)
        if self.status != "cancelled":
            if self.due_total <= Decimal("0.00"):
                self.status = "paid"
                if not self.paid_at:
                    self.paid_at = timezone.now()
            elif self.paid_total > Decimal("0.00"):
                self.status = "partial"
            else:
                self.status = "credit"


class SalesItem(models.Model):
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("herbalapp.Product", on_delete=models.PROTECT)

    qty = models.PositiveIntegerField(default=1)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))  # %

    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    line_subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    gst_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    line_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    def __str__(self) -> str:
        return f"{self.product.name} x {self.qty}"

    def calculate(self):
        qty = Decimal(int(self.qty))
        rate = money(self.rate)

        raw = (rate * qty).quantize(Decimal("0.01"))
        disc = (raw * money(self.discount_percent) / Decimal("100")).quantize(Decimal("0.01"))
        taxable = raw - disc
        gst = (taxable * money(self.gst_rate) / Decimal("100")).quantize(Decimal("0.01"))
        total = taxable + gst

        self.discount_amount = disc
        self.line_subtotal = taxable
        self.gst_amount = gst
        self.line_total = total


class PaymentTransaction(models.Model):
    MODES = [
        ("cash", "Cash"),
        ("upi", "UPI"),
        ("card", "Card"),
        ("bank", "Bank Transfer"),
    ]
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name="payments")
    mode = models.CharField(max_length=20, choices=MODES, default="cash")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    txn_ref = models.CharField(max_length=100, blank=True, default="")
    paid_on = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.invoice.invoice_no} - {self.mode} - {self.amount}"


# -----------------------------
# Stock Ledger (Truth)
# -----------------------------
class StockLedger(models.Model):
    REF_TYPES = [
        ("purchase", "Purchase"),
        ("sale", "Sale"),
        ("sale_return", "Sale Return"),
        ("adjust", "Adjustment"),
    ]

    product = models.ForeignKey("herbalapp.Product", on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    ref_type = models.CharField(max_length=20, choices=REF_TYPES)
    ref_id = models.PositiveIntegerField()  # PurchaseInvoice.id / SalesInvoice.id / Return id

    qty_in = models.IntegerField(default=0)
    qty_out = models.IntegerField(default=0)

    balance_after = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["product", "created_at"]),
            models.Index(fields=["ref_type", "ref_id"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.product.name} {self.ref_type} +{self.qty_in} -{self.qty_out} => {self.balance_after}"

    @staticmethod
    def current_balance(product_id: int) -> int:
        last = StockLedger.objects.filter(product_id=product_id).order_by("-id").first()
        return int(last.balance_after) if last else 0

    @staticmethod
    def apply_movement(product_id: int, ref_type: str, ref_id: int, qty_in: int = 0, qty_out: int = 0) -> StockLedger:
        """
        Atomic stock movement update.
        """
        with transaction.atomic():
            current = StockLedger.current_balance(product_id)
            new_bal = current + int(qty_in) - int(qty_out)
            entry = StockLedger.objects.create(
                product_id=product_id,
                ref_type=ref_type,
                ref_id=ref_id,
                qty_in=int(qty_in),
                qty_out=int(qty_out),
                balance_after=int(new_bal),
            )
            return entry


# -----------------------------
# Sales Returns (Stock IN back)
# -----------------------------
class SalesReturn(models.Model):
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.PROTECT, related_name="returns")
    return_date = models.DateField(default=timezone.localdate)
    refund_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Return for {self.invoice.invoice_no}"


class SalesReturnItem(models.Model):
    sales_return = models.ForeignKey(SalesReturn, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("herbalapp.Product", on_delete=models.PROTECT)
    qty = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return f"{self.product.name} x {self.qty}"

