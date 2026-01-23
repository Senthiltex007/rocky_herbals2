# ==========================================================
# herbalapp/signals.py
# FINAL STABLE VERSION – Auto activate & Income run
# ==========================================================
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from herbalapp.models import Member, DailyIncomeReport
from herbalapp.mlm_engine_binary_runner import run_binary_engine, run_daily_engine


@receiver(post_save, sender=Member)
def auto_activate_and_run_income(sender, instance, created, **kwargs):
    """
    Signals.py to:
    1. Auto activate new member
    2. Run binary eligibility & sponsor income
    3. Avoid duplicate income
    4. Auto run daily engine
    """
    join_date = timezone.now().date()

    # -------------------------
    # 1️⃣ Auto activate new member
    # -------------------------
    if not instance.is_active:
        instance.is_active = True
        instance.save(update_fields=["is_active"])

    # -------------------------
    # 2️⃣ Avoid duplicate income for the same member & date
    # -------------------------
    existing_report = DailyIncomeReport.objects.filter(
        member=instance,
        date=join_date
    ).first()
    if existing_report:
        # Already processed today
        return

    # -------------------------
    # 3️⃣ Run binary engine for this member
    # -------------------------
    new_report = run_binary_engine(instance, join_date)

    # -------------------------
    # 4️⃣ Sponsor income calculation
    # -------------------------
    sponsor = None
    if instance.placement_id == instance.sponsor_id:
        sponsor = instance.parent
    else:
        sponsor = Member.objects.filter(auto_id=instance.sponsor_id).first()

    if sponsor:
        sponsor_report, _ = DailyIncomeReport.objects.get_or_create(
            member=sponsor,
            date=join_date,
            defaults={
                "binary_income": Decimal("0"),
                "binary_eligibility_income": Decimal("0"),
                "sponsor_income": Decimal("0"),
                "flashout_wallet_income": Decimal("0"),
                "total_income": Decimal("0"),
                "left_cf": 0,
                "right_cf": 0,
            }
        )
        sponsor_add = new_report.binary_eligibility_income
        sponsor_report.sponsor_income += sponsor_add
        sponsor_report.total_income = (
            sponsor_report.binary_income
            + sponsor_report.binary_eligibility_income
            + sponsor_report.flashout_wallet_income
            + sponsor_report.sponsor_income
        )
        sponsor_report.save()

    # -------------------------
    # 5️⃣ Auto run daily MLM engine
    # -------------------------
    run_daily_engine(join_date)

