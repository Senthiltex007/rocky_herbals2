# ==========================================================
# 1) herbalapp/signals.py  ✅ STOP auto-trigger on member create
# ==========================================================
from django.db.models.signals import post_save
from django.dispatch import receiver
from herbalapp.models import Member
from herbalapp.models import RankReward

def run_monthly_rank_payout():
    for rr in RankReward.objects.filter(active=True):
        rr.credit_monthly_income()


@receiver(post_save, sender=Member)
def run_income_update_on_new_member(sender, instance, created, **kwargs):
    """
    ✅ IMPORTANT:
    We STOP auto-running the MLM engine on every new member.
    Because it causes:
    - partial runs
    - duplicate/half-processed flags
    - sponsor/binary mismatch until manual rerun
    """
    return  # ✅ disable completely (no celery call)

