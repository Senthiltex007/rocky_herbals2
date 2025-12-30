# herbalapp/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
from .models import Member, IncomeRecord
from .mlm_engine_binary import calculate_member_binary_income_for_day

SPONSOR_BONUS_AMOUNT = Decimal("500.00")  # sponsor eligibility bonus

@receiver(post_save, sender=Member)
def trigger_engine_on_new_member(sender, instance, created, **kwargs):
    if not created:
        return

    run_date = timezone.now().date()

    # 1️⃣ Create JOIN IncomeRecord for new member (avoid duplicates)
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

    placement = instance.placement
    sponsor = instance.sponsor
    if not placement:
        return  # root member has no placement

    # 2️⃣ Sponsor routing rules
    receiver = None
    if placement and sponsor:
        if placement.auto_id == sponsor.auto_id:
            # Rule 1: placement == sponsor → income goes to placement’s parent
            receiver = placement.parent
        else:
            # Rule 2: placement ≠ sponsor → income goes to sponsor
            receiver = sponsor

    # Rule 3: receiver must already have 1:1 pair
    if receiver and receiver.binary_eligible and receiver.has_completed_first_pair:
        # Avoid duplicate sponsor income for same day
        if not IncomeRecord.objects.filter(member=receiver, date=run_date, type="sponsor_income").exists():
            IncomeRecord.objects.create(
                member=receiver,
                date=run_date,
                type="sponsor_income",
                amount=SPONSOR_BONUS_AMOUNT,
                meta={"child": instance.auto_id, "placement": placement.auto_id, "sponsor": sponsor.auto_id}
            )
            receiver.total_sponsor_income += SPONSOR_BONUS_AMOUNT

    # 3️⃣ Count total left/right children for placement
    left_total = Member.objects.filter(placement=placement, side="left").count()
    right_total = Member.objects.filter(placement=placement, side="right").count()

    # ✅ Eligibility unlock check (1:1 pair)
    if left_total > 0 and right_total > 0 and not placement.binary_eligible:
        placement.binary_eligible = True
        placement.has_completed_first_pair = True
        # eligibility bonus once
        IncomeRecord.objects.get_or_create(
            member=placement,
            date=run_date,
            type="eligibility_bonus",
            defaults={"amount": SPONSOR_BONUS_AMOUNT}
        )

    # 4️⃣ Call binary engine
    result = calculate_member_binary_income_for_day(
        left_joins_today=left_total,
        right_joins_today=right_total,
        left_cf_before=placement.left_cf,
        right_cf_before=placement.right_cf,
        binary_eligible=placement.binary_eligible,
        member=placement,
        run_date=run_date
    )

    # 5️⃣ Update placement quick fields
    placement.lifetime_pairs += result.get("binary_pairs", 0)
    placement.left_cf = result.get("left_cf_after", placement.left_cf)
    placement.right_cf = result.get("right_cf_after", placement.right_cf)
    placement.repurchase_wallet_balance += result.get("repurchase_wallet_bonus", 0)

    Member.objects.filter(pk=placement.pk).update(
        binary_eligible=placement.binary_eligible,
        has_completed_first_pair=placement.has_completed_first_pair,
        lifetime_pairs=placement.lifetime_pairs,
        left_cf=placement.left_cf,
        right_cf=placement.right_cf,
        repurchase_wallet_balance=placement.repurchase_wallet_balance,
        total_sponsor_income=placement.total_sponsor_income
    )

    # 6️⃣ Create/Update IncomeRecord for placement (binary_engine)
    record, created = IncomeRecord.objects.get_or_create(
        member=placement,
        date=run_date,
        type="binary_engine",
        defaults={}
    )
    record.binary_income = result.get("binary_income", 0)
    record.sponsor_income = placement.total_sponsor_income
    record.flashout_units = result.get("flashout_units", 0)
    record.wallet_income = result.get("repurchase_wallet_bonus", 0)
    record.total_income = (
        record.binary_income +
        record.sponsor_income +
        record.wallet_income
    )
    record.save()

    print(f"⚡ Engine Triggered for {placement.auto_id} on {run_date}")

