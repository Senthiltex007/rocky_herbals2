# herbalapp/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Member, IncomeRecord
from .mlm_engine_binary import calculate_member_binary_income_for_day

@receiver(post_save, sender=Member)
def trigger_engine_on_new_member(sender, instance, created, **kwargs):
    if not created:
        return

    run_date = timezone.now().date()

    # 1️⃣ Create IncomeRecord for the NEW member (JOIN)
    IncomeRecord.objects.get_or_create(
        member=instance,
        date=run_date,
        type="JOIN",
        defaults={
            "left_joins": 0,
            "right_joins": 0,
            "total_income": 0,
        }
    )

    parent = instance.placement
    if not parent:
        return  # root member has no placement

    # 2️⃣ Count total left/right children for parent
    left_total = Member.objects.filter(placement=parent, side="left").count()
    right_total = Member.objects.filter(placement=parent, side="right").count()

    if left_total > 0 and right_total > 0 and not parent.binary_eligible:
        parent.binary_eligible = True

    # 3️⃣ Call binary engine
    result = calculate_member_binary_income_for_day(
        left_joins_today=left_total,
        right_joins_today=right_total,
        left_cf_before=parent.left_cf,
        right_cf_before=parent.right_cf,
        binary_eligible=parent.binary_eligible,
        member=parent,
        run_date=run_date
    )

    # 4️⃣ Update parent quick fields
    parent.lifetime_pairs += result.get("binary_pairs", 0)
    parent.left_cf = result.get("left_cf_after", parent.left_cf)
    parent.right_cf = result.get("right_cf_after", parent.right_cf)
    parent.repurchase_wallet_balance += result.get("repurchase_wallet_bonus", 0)

    Member.objects.filter(pk=parent.pk).update(
        binary_eligible=parent.binary_eligible,
        lifetime_pairs=parent.lifetime_pairs,
        left_cf=parent.left_cf,
        right_cf=parent.right_cf,
        repurchase_wallet_balance=parent.repurchase_wallet_balance
    )

    # 5️⃣ Create IncomeRecord for parent (binary_engine) safely
    IncomeRecord.objects.get_or_create(
        member=parent,
        date=run_date,
        type="binary_engine",
        defaults={
            "binary_income": result.get("binary_income", 0),
            "sponsor_income": result.get("eligibility_income", 0),
            "flashout_units": result.get("flashout_units", 0),
            "wallet_income": result.get("repurchase_wallet_bonus", 0),
            "total_income": result.get("total_income", 0),
        }
    )

    print(f"⚡ Engine Triggered for {parent.auto_id} on {run_date}")

