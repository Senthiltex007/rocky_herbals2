# herbalapp/signals.py
# ----------------------------------------------------------
# ✅ All old signals disabled for NEW MLM ENGINE
# ✅ Auto-trigger binary + sponsor engine when NEW member joins
# ----------------------------------------------------------

print("✅ signals.py loaded — all legacy signals disabled (new MLM engine active)")

from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date
from herbalapp.models import Member

@receiver(post_save, sender=Member)
def auto_trigger_engine(sender, instance, created, **kwargs):
    """
    ✅ This runs ONLY when a NEW member is created.
    ✅ It automatically triggers the binary engine for the sponsor.
    ✅ Sponsor income, binary income, and DailyIncomeReport update instantly.
    ✅ Buyer NEVER needs to run engine manually.
    """

    if not created:
        return  # Only run for NEW members

    new_member = instance
    sponsor = new_member.sponsor

    if not sponsor:
        return  # Root member or no sponsor → nothing to do

    # ✅ Count today's left/right joins for sponsor (CORRECTED)
    left_joins = (
        sponsor.left_member.get_new_members_today_count()
        if sponsor.left_member else 0
    )

    right_joins = (
        sponsor.right_member.get_new_members_today_count()
        if sponsor.right_member else 0
    )

    # ✅ Run engine for sponsor instantly
    try:
        sponsor.run_binary_engine_for_day(left_joins, right_joins)
        print(f"✅ Auto-engine triggered for sponsor: {sponsor.member_id}")
    except Exception as e:
        print(f"❌ Engine auto-trigger failed for {sponsor.member_id}: {e}")

