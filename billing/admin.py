# billing/admin.py
from django.contrib import admin, messages
from django.utils.html import format_html

from billing.models import (
    Customer, Supplier,
    PurchaseInvoice, PurchaseItem,
    SalesInvoice, SalesItem, PaymentTransaction,
    SalesReturn, SalesReturnItem,
    StockLedger, InvoiceSeries
)

from billing.services import (
    receive_purchase,
    finalize_invoice_totals,
    apply_stock_out_for_paid_invoice,
    apply_sales_return,
)


# ----------------------------
# Inline items
# ----------------------------
class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0


class SalesItemInline(admin.TabularInline):
    model = SalesItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = PaymentTransaction
    extra = 0


class SalesReturnItemInline(admin.TabularInline):
    model = SalesReturnItem
    extra = 0


# ----------------------------
# Customer / Supplier
# ----------------------------
@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "customer_type", "phone", "gstin", "state_code", "is_active", "created_at")
    search_fields = ("name", "phone", "gstin")
    list_filter = ("customer_type", "is_active", "state_code")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "gstin", "state_code", "is_active", "created_at")
    search_fields = ("name", "phone", "gstin")
    list_filter = ("is_active", "state_code")


# ----------------------------
# Purchase Admin
# ----------------------------
@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ("purchase_no", "supplier", "invoice_date", "status", "grand_total", "receive_btn")
    list_filter = ("status", "invoice_date")
    search_fields = ("purchase_no", "supplier__name", "invoice_ref")
    inlines = [PurchaseItemInline]

    def receive_btn(self, obj):
        if obj.status == "received":
            return "✅ Received"
        return format_html('<a class="button" href="receive/{}/">Receive + Stock IN</a>', obj.id)
    receive_btn.short_description = "Receive"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path("receive/<int:pk>/", self.admin_site.admin_view(self.receive_view), name="billing_purchase_receive"),
        ]
        return custom + urls

    def receive_view(self, request, pk: int):
        msg = receive_purchase(pk)
        messages.info(request, msg)
        from django.shortcuts import redirect
        return redirect("..")


# ----------------------------
# Sales Admin
# ----------------------------
@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_no", "invoice_type", "invoice_date", "status", "grand_total", "paid_total", "due_total", "actions_btn")
    list_filter = ("status", "invoice_type", "invoice_date")
    search_fields = ("invoice_no", "customer_name", "customer_phone", "customer__name", "customer__gstin")
    inlines = [SalesItemInline, PaymentInline]

    def actions_btn(self, obj):
        # show 2 buttons: Recalc + Stock OUT
        return format_html(
            '<a class="button" href="recalc/{}/">Recalc Totals</a> &nbsp; '
            '<a class="button" href="stockout/{}/">Stock OUT</a>',
            obj.id, obj.id
        )
    actions_btn.short_description = "Actions"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path("recalc/<int:pk>/", self.admin_site.admin_view(self.recalc_view), name="billing_sales_recalc"),
            path("stockout/<int:pk>/", self.admin_site.admin_view(self.stockout_view), name="billing_sales_stockout"),
        ]
        return custom + urls

    def recalc_view(self, request, pk: int):
        inv = SalesInvoice.objects.get(id=pk)
        finalize_invoice_totals(inv)
        messages.success(request, f"✅ Totals recalculated for {inv.invoice_no}. Status={inv.status}")
        from django.shortcuts import redirect
        return redirect("..")

    def stockout_view(self, request, pk: int):
        msg = apply_stock_out_for_paid_invoice(pk)
        messages.info(request, msg)
        from django.shortcuts import redirect
        return redirect("..")


# ----------------------------
# Sales Return Admin
# ----------------------------
@admin.register(SalesReturn)
class SalesReturnAdmin(admin.ModelAdmin):
    list_display = ("invoice", "return_date", "refund_total", "apply_btn")
    list_filter = ("return_date",)
    search_fields = ("invoice__invoice_no",)
    inlines = [SalesReturnItemInline]

    def apply_btn(self, obj):
        return format_html('<a class="button" href="apply/{}/">Apply Return Stock IN</a>', obj.id)
    apply_btn.short_description = "Apply"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path("apply/<int:pk>/", self.admin_site.admin_view(self.apply_view), name="billing_return_apply"),
        ]
        return custom + urls

    def apply_view(self, request, pk: int):
        msg = apply_sales_return(pk)
        messages.info(request, msg)
        from django.shortcuts import redirect
        return redirect("..")


# ----------------------------
# Stock Ledger + Series
# ----------------------------
@admin.register(StockLedger)
class StockLedgerAdmin(admin.ModelAdmin):
    list_display = ("product", "ref_type", "ref_id", "qty_in", "qty_out", "balance_after", "created_at")
    list_filter = ("ref_type", "created_at")
    search_fields = ("product__name",)


@admin.register(InvoiceSeries)
class InvoiceSeriesAdmin(admin.ModelAdmin):
    list_display = ("key", "last_number", "updated_at")
    search_fields = ("key",)

