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
# herbalapp/admin.py
from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _
from datetime import datetime
from herbalapp.models import EngineLock, DailyIncomeReport, SponsorIncomeLog

@admin.register(EngineLock)
class EngineLockAdmin(admin.ModelAdmin):
    list_display = ("run_date", "is_running", "started_at", "finished_at")
    list_filter = ("is_running", "run_date")
    ordering = ("-run_date",)

    change_list_template = "admin/engine_lock_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("run-engine/", self.admin_site.admin_view(self.run_engine_view), name="run_engine_view"),
        ]
        return custom_urls + urls

    def run_engine_view(self, request):
        if request.method == "POST":
            date_str = request.POST.get("run_date", "").strip()
            if not date_str:
                messages.error(request, "⛔ Date கொடுக்கவில்லை.")
                return redirect("..")

            try:
                run_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "⛔ தவறான date format. YYYY-MM-DD format பயன்படுத்தவும்.")
                return redirect("..")

            # ✅ Run engine
            from herbalapp.mlm.manual_engine import run_engine_for_date
            result_msg = run_engine_for_date(run_date)

            if result_msg.startswith("✅"):
                messages.success(request, result_msg)
            elif result_msg.startswith("⛔"):
                messages.warning(request, result_msg)
            else:
                messages.error(request, result_msg)

            return redirect("..")

        context = dict(
            self.admin_site.each_context(request),
            title="Manual MLM Engine Run",
        )
        return render(request, "admin/manual_engine_run.html", context)

