# ==========================================================
# herbalapp/signals.py
# AUTO RUN DAILY ENGINE + AUDIT ON NEW MEMBER JOIN
# ==========================================================

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction

from herbalapp.models import Member
from herbalapp.mlm.utils import run_daily_engine  # அல்லது mlm_run_full_daily version
from herbalapp.mlm.audit import print_audit_summary

ROOT_ID = "rocky004"

@receiver(post_save, sender=Member)
def auto_run_daily_engine_on_join(sender, instance, created, **kwargs):
    """
    ✅ Trigger DAILY MLM ENGINE + AUTO AUDIT when a new member joins
    ❌ Avoid duplicates: Only runs if member is created and not ROOT
    """

    if not created:
        return

    if instance.auto_id == ROOT_ID:
        return

    run_date = timezone.localdate()

    # Run daily engine for today inside transaction
    try:
        with transaction.atomic():
            run_daily_engine(run_date)  # FULL binary + sponsor engine
            print(f"🚀 Daily engine executed for new member {instance.member_id} on {run_date}")

            # Run audit automatically
            print_audit_summary(run_date)

    except Exception as e:
        print(f"❌ Error running daily engine for new member {instance.member_id}: {e}")

