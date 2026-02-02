from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import (
    Member, Payment, Commission, Product, Order,
    IncomeRecord, CommissionRecord, BonusRecord, RockCounter,
    RankReward, RankPayoutLog, DailyIncomeReport
)
#from .tasks import run_engine_task  # ✅ Celery task import

# ==========================================================
# ✅ MEMBER ADMIN (UPDATED FOR NEW BINARY + RANK ENGINE)
# ==========================================================
@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "id", "auto_id_display", "name", "sponsor", "package", "total_bv_display",
        "binary_income_display", "sponsor_income_display",
        "flashout_income_display", "salary_income_display",
        "current_rank", "joined_date", "active"
    )
    search_fields = ("auto_id", "name", "phone", "email")
    list_filter = ("package", "side", "active", "district", "taluk", "current_rank")
    ordering = ("id",)

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
        total = DailyIncomeReport.objects.filter(
            member=obj
        ).aggregate(
            total=Sum("binary_income")
        )["total"] or 0
        return total
    binary_income_display.short_description = "Binary Income"

    # ✅ Sponsor Income
    def sponsor_income_display(self, obj):
        total = DailyIncomeReport.objects.filter(
            member=obj
        ).aggregate(
            total=Sum("sponsor_income")
        )["total"] or 0
        return total
    sponsor_income_display.short_description = "Sponsor Income"

    # ✅ Flashout Bonus
    def flashout_income_display(self, obj):
        total = DailyIncomeReport.objects.filter(
            member=obj
        ).aggregate(
            total=Sum("flash_bonus")
        )["total"] or 0
        return total
    flashout_income_display.short_description = "Flashout Bonus"

    # ✅ Salary Income
    def salary_income_display(self, obj):
        total = DailyIncomeReport.objects.filter(
            member=obj
        ).aggregate(
            total=Sum("salary_income")
        )["total"] or 0
        return total
    salary_income_display.short_description = "Salary Income"

    # ✅ Override save_model to trigger engine
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # 🔹 Only trigger engine for NEW member
        if not change:
            run_engine_task.delay()  # Celery async engine run


# ==========================================================
# ✅ OTHER ADMINS (PAYMENT, PRODUCT, RANK)
# ==========================================================
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "member", "amount", "status", "date")
    search_fields = ("member__name", "status")
    list_filter = ("status", "date")

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "mrp", "bv_value", "created_at")
    search_fields = ("name",)
    list_filter = ("created_at",)

@admin.register(RankReward)
class RankRewardAdmin(admin.ModelAdmin):
    list_display = ("member", "rank_title", "monthly_income", "duration_months", "months_paid", "active")
    list_filter = ("rank_title", "active")
    search_fields = ("member__auto_id", "member__name")

@admin.register(RankPayoutLog)
class RankPayoutLogAdmin(admin.ModelAdmin):
    list_display = ("member", "rank_reward", "amount", "paid_on")
    list_filter = ("paid_on",)
    search_fields = ("member__auto_id", "member__name")


# ==========================================================
# ✅ OTHER REGISTRATIONS
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

