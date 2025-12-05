from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Member, Payment, Income, Commission, Product, Order,
    IncomeRecord, CommissionRecord, BonusRecord, RockCounter,
    RankReward, RankPayoutLog
)

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "id", "auto_id_display", "name", "sponsor", "package", "bv",
        "binary_income_display", "sponsor_income_display",
        "flash_bonus_display", "salary_display", "stock_commission_display",
        "current_rank", "joined_date", "active"
    )
    search_fields = ("auto_id", "name", "phone", "email")
    list_filter = ("package", "side", "active", "district", "taluk", "current_rank")
    ordering = ("id",)
    actions = ["recalculate_income"]

    def auto_id_display(self, obj):
        return format_html("<strong>{}</strong>", obj.auto_id)
    auto_id_display.short_description = "Auto ID"

    def binary_income_display(self, obj):
        return obj.calculate_full_income().get("binary_income", 0)
    binary_income_display.short_description = "Binary Income"

    def sponsor_income_display(self, obj):
        return obj.calculate_full_income().get("sponsor_income", 0)
    sponsor_income_display.short_description = "Sponsor Income"

    def flash_bonus_display(self, obj):
        return obj.calculate_full_income().get("flash_bonus", 0)
    flash_bonus_display.short_description = "Flash Bonus"

    def salary_display(self, obj):
        return obj.calculate_full_income().get("salary", 0)
    salary_display.short_description = "Salary Slab"

    def stock_commission_display(self, obj):
        return obj.calculate_full_income().get("stock_commission", 0)
    stock_commission_display.short_description = "Stock Commission"

    def recalculate_income(self, request, queryset):
        for member in queryset:
            income = member.calculate_full_income()
            member.binary_income = income.get("binary_income", 0)
            member.sponsor_income = income.get("sponsor_income", 0)
            member.flash_bonus = income.get("flash_bonus", 0)
            member.salary_income = income.get("salary", 0)
            member.stock_commission = income.get("stock_commission", 0)
            member.save()
        self.message_user(request, "Income recalculated for selected members.")
    recalculate_income.short_description = "Recalculate Income"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "member", "amount", "status", "date")
    search_fields = ("member__name", "status")
    list_filter = ("status", "date")


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = (
        "id", "member", "date",
        "joining_package", "binary_pairs", "binary_income",
        "sponsor_income", "flash_out_bonus", "salary_income"
    )
    search_fields = ("member__name",)
    list_filter = ("date",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "mrp", "created_at")
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


# Register remaining models directly
admin.site.register(Commission)
admin.site.register(Order)
admin.site.register(IncomeRecord)
admin.site.register(CommissionRecord)
admin.site.register(BonusRecord)
admin.site.register(RockCounter)

# ✅ Optional: Customize admin site branding
admin.site.site_header = "🌿 Rocky Herbals Administration"
admin.site.site_title = "Rocky Herbals Admin"
admin.site.index_title = "Welcome to Rocky Herbals Dashboard"

