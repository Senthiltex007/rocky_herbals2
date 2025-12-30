# ==========================================================
# herbalapp/admin.py (FINAL CLEAN VERSION)
# ==========================================================
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
# ✅ MEMBER ADMIN (MANUAL ID VERSION)
# ==========================================================
@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "member_id",
        "name",
        "phone",
        "email",
        "aadhar_number",
        "side",
        "position",
        "joined_date",
    )
    search_fields = ("member_id", "name", "phone", "email")
    list_filter = ("side", "position", "is_active")
    ordering = ("member_id",)


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
        "eligibility_income",
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
    search_fields = ("member__member_id", "member__name")


# ==========================================================
# ✅ RANK PAYOUT LOG ADMIN
# ==========================================================
@admin.register(RankPayoutLog)
class RankPayoutLogAdmin(admin.ModelAdmin):
    list_display = ("member", "rank_reward", "amount", "paid_on")
    list_filter = ("paid_on",)
    search_fields = ("member__member_id", "member__name")


# ==========================================================
# ✅ INCOME RECORD ADMIN
# ==========================================================
@admin.register(IncomeRecord)
class IncomeRecordAdmin(admin.ModelAdmin):
    list_display = [
        "member",
        "type",
        "amount",
        "eligibility_income",
        "binary_income",
        "sponsor_income",
        "wallet_income",
        "salary_income",
        "total_income",
        "created_at",
    ]
    search_fields = ["member__name", "member__member_id"]
    list_filter = ["type", "created_at"]


# ==========================================================
# ✅ DIRECT REGISTRATIONS
# ==========================================================
admin.site.register(BonusRecord)
admin.site.register(RockCounter)

# ==========================================================
# ✅ Admin Branding
# ==========================================================
admin.site.site_header = "🌿 Rocky Herbals Administration"
admin.site.site_title = "Rocky Herbals Admin"
admin.site.index_title = "Welcome to Rocky Herbals Dashboard"

