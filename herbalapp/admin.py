from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Member, Payment, Income, Commission, Product, Order,
    IncomeRecord, CommissionRecord, BonusRecord, RockCounter,
    RankReward, RankPayoutLog
)

# ==========================================================
# ✅ MEMBER ADMIN (UPDATED + joined_date READ-ONLY)
# ==========================================================
@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "id", "auto_id_display", "name", "sponsor", "package",
        "total_bv_display", "binary_income_display",
        "sponsor_income_display", "flashout_income_display",
        "salary_display", "current_rank", "joined_date", "active"
    )

    search_fields = ("auto_id", "name", "phone", "email")
    list_filter = ("package", "side", "active", "district", "taluk", "current_rank")
    ordering = ("id",)

    # ✅ Make joined_date read-only in admin form
    readonly_fields = ("joined_date",)

    # ✅ Ensure joined_date is read-only in both Add & Edit forms
    def get_readonly_fields(self, request, obj=None):
        # obj == None → Add form
        # obj != None → Edit form
        return ("joined_date",)

    # ✅ Auto ID highlight
    def auto_id_display(self, obj):
        return format_html("<strong>{}</strong>", obj.auto_id)
    auto_id_display.short_description = "Auto ID"

    # ✅ Total BV (Left / Right)
    def total_bv_display(self, obj):
        return f"{obj.total_left_bv} / {obj.total_right_bv}"
    total_bv_display.short_description = "Left / Right BV"

    # ✅ Binary Income
    def binary_income_display(self, obj):
        total = Income.objects.filter(member=obj).aggregate_sum("binary_income")
        return total or 0
    binary_income_display.short_description = "Binary Income"

    # ✅ Sponsor Income
    def sponsor_income_display(self, obj):
        total = Income.objects.filter(member=obj).aggregate_sum("sponsor_income")
        return total or 0
    sponsor_income_display.short_description = "Sponsor Income"

    # ✅ Flashout Income
    def flashout_income_display(self, obj):
        total = Income.objects.filter(member=obj).aggregate_sum("flash_bonus")
        return total or 0
    flashout_income_display.short_description = "Flashout Bonus"

    # ✅ Salary (Rank Reward Monthly Salary)
    def salary_display(self, obj):
        return obj.salary or 0
    salary_display.short_description = "Monthly Salary"


# ==========================================================
# ✅ PAYMENT ADMIN
# ==========================================================
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "member", "amount", "status", "date")
    search_fields = ("member__name", "status")
    list_filter = ("status", "date")


# ==========================================================
# ✅ INCOME ADMIN
# ==========================================================
@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = (
        "id", "member", "date",
        "binary_pairs", "binary_income",
        "sponsor_income", "flash_bonus", "salary_income"
    )
    search_fields = ("member__name",)
    list_filter = ("date",)


# ==========================================================
# ✅ PRODUCT ADMIN
# ==========================================================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "mrp", "bv_value", "created_at")
    search_fields = ("name",)
    list_filter = ("created_at",)


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
admin.site.register(Commission)
admin.site.register(Order)
admin.site.register(IncomeRecord)
admin.site.register(CommissionRecord)
admin.site.register(BonusRecord)
admin.site.register(RockCounter)

# ✅ Admin Branding
admin.site.site_header = "🌿 Rocky Herbals Administration"
admin.site.site_title = "Rocky Herbals Admin"
admin.site.index_title = "Welcome to Rocky Herbals Dashboard"

