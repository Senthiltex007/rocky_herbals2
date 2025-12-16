# herbalapp/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Member, Product, Payment, Income, Commission,
    Order, SponsorIncome, DailyIncomeReport,
    RankReward, RankPayoutLog, IncomeRecord,
    CommissionRecord, BonusRecord, RockCounter
)

# ==========================================================
# ✅ MEMBER ADMIN
# ==========================================================
@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "auto_id_display",
        "name",
        "sponsor",
        "side",
        "binary_eligible",
        "has_completed_first_pair",
        "left_cf",
        "right_cf",
        "joined_date",
    )

    search_fields = ("auto_id", "name", "phone", "email")
    list_filter = ("side", "binary_eligible", "has_completed_first_pair", "district", "taluk", "pincode")
    ordering = ("id",)
    readonly_fields = ("joined_date",)

    def auto_id_display(self, obj):
        return format_html("<strong>{}</strong>", obj.auto_id)
    auto_id_display.short_description = "Auto ID"


# ==========================================================
# ✅ PRODUCT ADMIN
# ==========================================================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["product_id", "name", "mrp", "bv_value", "created_at"]
    search_fields = ["product_id", "name"]


# ==========================================================
# ✅ ORDER ADMIN
# ==========================================================
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "member", "product", "quantity", "total_amount", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["member__name", "product__name"]


# ==========================================================
# ✅ PAYMENT ADMIN
# ==========================================================
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["member", "amount", "status", "date"]
    list_filter = ["status"]
    search_fields = ["member__name"]


# ==========================================================
# ✅ INCOME ADMIN
# ==========================================================
@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ["member", "date", "binary_income", "sponsor_income", "flash_bonus", "salary_income"]
    search_fields = ["member__name"]


# ==========================================================
# ✅ SPONSOR INCOME ADMIN
# ==========================================================
@admin.register(SponsorIncome)
class SponsorIncomeAdmin(admin.ModelAdmin):
    list_display = ["sponsor", "child", "amount", "date"]
    search_fields = ["sponsor__name", "child__name"]


# ==========================================================
# ✅ COMMISSION ADMIN
# ==========================================================
@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ["member", "commission_type", "commission_amount", "date"]
    list_filter = ["commission_type"]
    search_fields = ["member__name"]


# ==========================================================
# ✅ DAILY INCOME REPORT ADMIN
# ==========================================================
@admin.register(DailyIncomeReport)
class DailyIncomeReportAdmin(admin.ModelAdmin):
    list_display = [
        "member",
        "date",
        "left_joins",
        "right_joins",
        "binary_pairs_paid",
        "binary_income",
        "sponsor_income",
        "total_income",
    ]
    search_fields = ["member__name"]


# ==========================================================
# ✅ RANK REWARD ADMIN
# ==========================================================
@admin.register(RankReward)
class RankRewardAdmin(admin.ModelAdmin):
    list_display = ("member", "rank_title", "monthly_income", "duration_months", "months_paid", "active")
    list_filter = ("rank_title", "active")
    search_fields = ("member__auto_id", "member__name")


# ==========================================================
# ✅ RANK PAYOUT LOG ADMIN
# ==========================================================
@admin.register(RankPayoutLog)
class RankPayoutLogAdmin(admin.ModelAdmin):
    list_display = ("member", "rank_reward", "amount", "paid_on")
    list_filter = ("paid_on",)
    search_fields = ("member__auto_id", "member__name")


# ==========================================================
# ✅ DIRECT REGISTRATIONS
# ==========================================================
admin.site.register(IncomeRecord)
admin.site.register(CommissionRecord)
admin.site.register(BonusRecord)
admin.site.register(RockCounter)

# ✅ Admin Branding
admin.site.site_header = "🌿 Rocky Herbals Administration"
admin.site.site_title = "Rocky Herbals Admin"
admin.site.index_title = "Welcome to Rocky Herbals Dashboard"

