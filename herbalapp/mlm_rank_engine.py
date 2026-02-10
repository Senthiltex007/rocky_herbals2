# herbalapp/mlm_rank_engine.py

from django.db import transaction
from django.utils import timezone
from herbalapp.rank_rules import RANK_SLABS
from herbalapp.models import RankReward


def get_next_rank(level):
    if level < 0 or level >= len(RANK_SLABS):
        return None
    return RANK_SLABS[level]


@transaction.atomic
def process_rank_upgrade(member):
    """
    Life-time BV based rank upgrade.
    Each rank resets BV counter for next rank.
    """

    bv_data = member.calculate_bv()
    total_matched_bv = int(bv_data["matched_bv"])

    upgraded = False

    while True:
        next_rank = get_next_rank(member.rank_level)
        if not next_rank:
            break

        required_bv, title, monthly, months = next_rank
        progress_bv = total_matched_bv - member.rank_checkpoint_bv

        # ❌ Not enough BV for next rank
        if progress_bv < required_bv:
            break

        # ✅ Create RankReward (avoid duplicates)
        RankReward.objects.get_or_create(
            member=member,
            rank_title=title,
            defaults={
                "left_bv_snapshot": int(bv_data["left_bv"]),
                "right_bv_snapshot": int(bv_data["right_bv"]),
                "monthly_income": monthly,
                "duration_months": months,
                "start_date": timezone.now().date(),
            }
        )

        # ✅ Upgrade member
        member.current_rank = title
        member.rank_level += 1
        member.rank_checkpoint_bv += required_bv
        member.rank_assigned_at = timezone.now()
        member.save(update_fields=[
            "current_rank",
            "rank_level",
            "rank_checkpoint_bv",
            "rank_assigned_at"
        ])

        upgraded = True

    return upgraded

