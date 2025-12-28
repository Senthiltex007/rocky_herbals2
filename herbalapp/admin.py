# herbalapp/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Member,
    IncomeRecord,
    BonusRecord,
    Order,
    Payment,
    Income,
    SponsorIncome,
    Commission,
    DailyIncomeReport,
    RankReward,
    RankPayoutLog,
    RockCounter,
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
# ✅ DAILY INCOME REPORT ADMIN (minimal change: only eligibility_income added)
# ==========================================================
@admin.register(DailyIncomeReport)
class DailyIncomeReportAdmin(admin.ModelAdmin):
    list_display = [
        "member",
        "date",
        "left_joins",
        "right_joins",
        "binary_pairs_paid",
        "eligibility_income",   # ✅ added
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
# ✅ INCOME RECORD ADMIN (new: explicit admin with eligibility field)
# ==========================================================
@admin.register(IncomeRecord)
class IncomeRecordAdmin(admin.ModelAdmin):
    list_display = [
        "member",
        "type",
        "amount",
        "eligibility_income",   # ✅ added
        "binary_income",
        "sponsor_income",
        "wallet_income",
        "salary_income",
        "total_income",
        "created_at",
    ]
    search_fields = ["member__name", "member__auto_id"]
    list_filter = ["type", "created_at"]


# ==========================================================
# ✅ DIRECT REGISTRATIONS (unchanged)
# ==========================================================
admin.site.register(BonusRecord)
admin.site.register(RockCounter)

# ✅ Admin Branding (unchanged)
admin.site.site_header = "🌿 Rocky Herbals Administration"
admin.site.site_title = "Rocky Herbals Admin"
admin.site.index_title = "Welcome to Rocky Herbals Dashboard"

