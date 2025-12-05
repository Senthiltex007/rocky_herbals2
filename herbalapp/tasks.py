from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .models import RankReward

def run_monthly_rank_payouts():
    """
    Run monthly payouts for all active RankRewards.
    Credits monthly income until duration is complete.
    """
    today = timezone.now().date()
    rewards = RankReward.objects.filter(
        active=True,
        months_paid__lt=F("duration_months")
    ).order_by("id")

    for reward in rewards:
        with transaction.atomic():
            reward.credit_monthly_income()

