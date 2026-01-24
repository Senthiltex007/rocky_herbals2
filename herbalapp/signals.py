# ==========================================================
# herbalapp/signals.py  ✅ FINAL & CLEAN
# ==========================================================

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from herbalapp.models import Member, DailyIncomeReport

ROOT_ID = "rocky001"

# ----------------------------------------------------------
# Signal: Create DailyIncomeReport ONLY
# ❌ No income calculation here
# ----------------------------------------------------------
@receiver(post_save, sender=Member)
def create_daily_income_report(sender, instance, created, **kwargs):

    # Skip root & updates
    if not created or instance.auto_id == ROOT_ID:
        return

    run_date = instance.joined_date or timezone.localdate()

    DailyIncomeReport.objects.get_or_create(
        member=instance,
        date=run_date,
        defaults={
            "binary_income": 0,
            "binary_eligibility_income": 0,
            "sponsor_income": 0,
            "flashout_wallet_income": 0,
            "total_income": 0,
            "left_cf": 0,
            "right_cf": 0,
            "sponsor_processed": False,
        }
    )

    print(f"📄 DailyIncomeReport created for {instance.auto_id} ({run_date})")

