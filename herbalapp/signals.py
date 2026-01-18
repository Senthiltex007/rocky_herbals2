# herbalapp/signals.py
# ==========================================================
# SAFE SIGNALS FILE (NO MLM ENGINES)
# ==========================================================

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from herbalapp.models import Member, DailyIncomeReport

ROOT_ID = "rocky004"


@receiver(post_save, sender=Member)
def create_daily_report_on_join(sender, instance, created, **kwargs):
    """
    SAFE SIGNAL
    - Only ensures DailyIncomeReport exists
    - NO income calculation here
    - NO MLM engine calls
    """

    if not created:
        return

    if instance.auto_id == ROOT_ID:
        return

    run_date = timezone.localdate()

    DailyIncomeReport.objects.get_or_create(
        member=instance,
        date=run_date,
        defaults={
            "binary_eligibility_income": 0,
            "binary_income": 0,
            "flashout_wallet_income": 0,
            "sponsor_income": 0,
            "total_income": 0,
        }
    )

    # ⚠️ DO NOT call instance.save() inside signal

