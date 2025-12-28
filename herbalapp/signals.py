# herbalapp/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from herbalapp.models import Member, IncomeRecord
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day

@receiver(post_save, sender=Member)
def trigger_engine_on_new_member(sender, instance, created, **kwargs):
    if not created:
        return

    # ✅ Run engine for the parent (placement), not the new child itself
    parent = instance.placement
    if not parent:
        return  # root member has no placement, skip

    run_date = timezone.now().date()

    # ✅ Count today's left/right joins under this parent
    left_joins_today = Member.objects.filter(
        placement=parent, side="left", joined_date=run_date
    ).count()
    right_joins_today = Member.objects.filter(
        placement=parent, side="right", joined_date=run_date
    ).count()

    # ✅ Check if engine already ran for this parent today
    already_record = IncomeRecord.objects.filter(
        member=parent,
        type="binary_engine",
        created_at__date=run_date
    ).exists()
    if already_record:
        print(f"⚠ Engine already triggered for {parent.auto_id} on {run_date}, skipping duplicate run.")
        return

    # ✅ Call engine for parent
    result = calculate_member_binary_income_for_day(
        left_joins_today,
        right_joins_today,
        parent.left_cf,
        parent.right_cf,
        parent.binary_eligible,
        parent,
        run_date
    )

    # ✅ Snapshot CF before update
    left_cf_before = parent.left_cf
    right_cf_before = parent.right_cf

    # ✅ Update eligibility
    if result["new_binary_eligible"] and not parent.binary_eligible:
        parent.binary_eligible = True

    # ✅ Update lifetime pairs
    parent.lifetime_pairs += result["binary_pairs"]

    # ✅ Update carry forward safely
    parent.left_cf = result["left_cf_after"]
    parent.right_cf = result["right_cf_after"]

    # ✅ Update repurchase wallet balance (spot)
    if result["repurchase_wallet_bonus"] > 0:
        parent.repurchase_wallet_balance += result["repurchase_wallet_bonus"]

    # ✅ Use update() to avoid recursion
    Member.objects.filter(pk=parent.pk).update(
        binary_eligible=parent.binary_eligible,
        lifetime_pairs=parent.lifetime_pairs,
        left_cf=parent.left_cf,
        right_cf=parent.right_cf,
        repurchase_wallet_balance=parent.repurchase_wallet_balance
    )

    # 🔍 Audit log — full details
    print(f"⚡ Engine Triggered for {parent.auto_id} on {run_date}")
    print(f"   Eligibility unlocked: {result['became_eligible_today']} (Eligible={result['new_binary_eligible']})")
    print(f"   Eligibility bonus: ₹{result['eligibility_income']}")
    print(f"   Binary pairs: {result['binary_pairs']} → Binary income: ₹{result['binary_income']}")
    print(f"   Flashout units: {result['flashout_units']} → Wallet bonus: ₹{result['repurchase_wallet_bonus']}")
    print(f"   Repurchase wallet balance updated: ₹{parent.repurchase_wallet_balance}")
    print(f"   Washed pairs: {result['washed_pairs']}")
    print(f"   Carry forward → Left={result['left_cf_after']}, Right={result['right_cf_after']}")
    print(f"   Sponsor mirrored: ₹{result['child_total_for_sponsor']}")
    print(f"   Total income credited: ₹{result['total_income']}")

    # ✅ Save IncomeRecord with eligibility bonus
    IncomeRecord.objects.create(
        member=parent,
        type="binary_engine",
        amount=result["total_income"],
        created_at=timezone.now(),
        left_joins=left_joins_today,
        right_joins=right_joins_today,
        left_cf_before=left_cf_before,
        right_cf_before=right_cf_before,
        left_cf_after=result["left_cf_after"],
        right_cf_after=result["right_cf_after"],
        binary_pairs=result["binary_pairs"],
        binary_income=result["binary_income"],
        sponsor_income=result["child_total_for_sponsor"],
        flashout_units=result["flashout_units"],
        wallet_income=result["repurchase_wallet_bonus"],
        washed_pairs=result["washed_pairs"],
        eligibility_income=result["eligibility_income"],   # ✅ important
        salary_income=0,  # or from rank calc if available
        total_income=result["total_income"]
    )

