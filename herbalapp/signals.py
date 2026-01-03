# herbalapp/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
from django.db import models

from .models import Member, IncomeRecord, DailyIncomeReport
from .mlm_engine_binary import calculate_member_binary_income_for_day

ELIGIBILITY_BONUS_AMOUNT = Decimal("500.00")


@receiver(post_save, sender=Member)
def trigger_engine_on_new_member(sender, instance, created, **kwargs):
    if not created:
        return

    run_date = timezone.now().date()

    # --------------------------------------------------
    # 1️⃣ Ensure DailyIncomeReport exists for new member
    # --------------------------------------------------
    DailyIncomeReport.objects.get_or_create(
        member=instance,
        date=run_date,
        defaults={
            "eligibility_income": Decimal("0.00"),
            "binary_income": Decimal("0.00"),
            "sponsor_income": Decimal("0.00"),
            "wallet_income": Decimal("0.00"),
            "salary_income": Decimal("0.00"),
            "total_income": Decimal("0.00"),
        }
    )

    placement = instance.placement
    sponsor = instance.sponsor

    if not placement:
        return  # ROOT member

    # --------------------------------------------------
    # 2️⃣ Count LEFT / RIGHT joins for placement
    # --------------------------------------------------
    left_total = Member.objects.filter(placement=placement, side="left").count()
    right_total = Member.objects.filter(placement=placement, side="right").count()

    # --------------------------------------------------
    # 3️⃣ Eligibility unlock (2:1 or 1:2)
    # --------------------------------------------------
    eligibility_today = False

    if not placement.binary_eligible:
        if (left_total >= 2 and right_total >= 1) or (left_total >= 1 and right_total >= 2):
            placement.binary_eligible = True
            placement.has_completed_first_pair = True
            eligibility_today = True

            if not placement.eligibility_bonus_given:
                placement.eligibility_bonus_given = True

                # IncomeRecord (Eligibility) — always create, no duplicates
                IncomeRecord.objects.create(
                    member=placement,
                    date=run_date,
                    type="eligibility_bonus",
                    amount=ELIGIBILITY_BONUS_AMOUNT
                )

                # ✅ DailyIncomeReport update (CORRECT COLUMN)
                report, created = DailyIncomeReport.objects.get_or_create(
                    member=placement,
                    date=run_date,
                    defaults={
                        "eligibility_income": ELIGIBILITY_BONUS_AMOUNT,
                        "binary_income": Decimal("0.00"),
                        "sponsor_income": Decimal("0.00"),
                        "wallet_income": Decimal("0.00"),
                        "salary_income": Decimal("0.00"),
                        "total_income": ELIGIBILITY_BONUS_AMOUNT,
                    }
                )
                if not created:
                    report.eligibility_income += ELIGIBILITY_BONUS_AMOUNT
                    report.total_income = (
                        report.eligibility_income +
                        report.binary_income +
                        report.sponsor_income +
                        report.wallet_income +
                        report.salary_income
                    )
                    report.save()

            placement.save(update_fields=[
                "binary_eligible",
                "has_completed_first_pair",
                "eligibility_bonus_given",
            ])

    # --------------------------------------------------
    # Sponsor income routing (Permanent Fix)
    # --------------------------------------------------
    receiver_member = None
    if placement and sponsor:
        if placement.auto_id == sponsor.auto_id:
            receiver_member = placement.parent or placement
        else:
            receiver_member = sponsor

    sponsor_amount = Decimal("0.00")

    if (
        receiver_member
        and receiver_member.binary_eligible
        and receiver_member.has_completed_first_pair
    ):
        # ✅ Ensure child eligibility bonus record exists
        child_eligibility_today = False
        left_count = Member.objects.filter(placement=instance, side="left").count()
        right_count = Member.objects.filter(placement=instance, side="right").count()

        if (left_count >= 2 and right_count >= 1) or (left_count >= 1 and right_count >= 2):
            if not instance.eligibility_bonus_given:
                IncomeRecord.objects.create(
                    member=instance,
                    date=run_date,
                    type="eligibility_bonus",
                    amount=ELIGIBILITY_BONUS_AMOUNT
                )
                instance.binary_eligible = True
                instance.has_completed_first_pair = True
                instance.eligibility_bonus_given = True
                instance.save(update_fields=[
                    "binary_eligible",
                    "has_completed_first_pair",
                    "eligibility_bonus_given",
                ])
            child_eligibility_today = True

        child_eligibility = ELIGIBILITY_BONUS_AMOUNT if child_eligibility_today else Decimal("0.00")

        child_sponsor = IncomeRecord.objects.filter(
            member=instance,
            date=run_date,
            type="sponsor_income"
        ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

        sponsor_amount = child_eligibility + child_sponsor

        if sponsor_amount > 0:
            IncomeRecord.objects.create(
                member=receiver_member,
                date=run_date,
                type="sponsor_income",
                amount=sponsor_amount
            )
            receiver_member.total_sponsor_income += sponsor_amount
            receiver_member.save(update_fields=["total_sponsor_income"])

    # --------------------------------------------------
    # 5️⃣ Binary engine (Eligibility day pair EXCLUDED)
    # --------------------------------------------------
    result = calculate_member_binary_income_for_day(
        left_joins_today=left_total,
        right_joins_today=right_total,
        left_cf_before=placement.left_cf,
        right_cf_before=placement.right_cf,
        binary_eligible=placement.binary_eligible,
        eligibility_today=eligibility_today,   # 🔥 IMPORTANT FLAG
        member=placement,
        run_date=run_date
    )

    # 🔹 Block binary income on eligibility unlock day
    if eligibility_today:
        result["binary_income"] = Decimal("0.00")
        # lock the pair so it cannot be reused
        placement.locked_pairs = getattr(placement, "locked_pairs", 0) + 1

    # --------------------------------------------------
    # 6️⃣ Update placement stats
    # --------------------------------------------------
    placement.lifetime_pairs += result.get("binary_pairs", 0)
    placement.left_cf = result.get("left_cf_after", placement.left_cf)
    placement.right_cf = result.get("right_cf_after", placement.right_cf)
    placement.repurchase_wallet_balance += result.get("repurchase_wallet_bonus", 0)

    placement.save(update_fields=[
        "lifetime_pairs",
        "left_cf",
        "right_cf",
        "repurchase_wallet_balance",
        "total_sponsor_income",
        "locked_pairs",
    ])

    # --------------------------------------------------
    # 7️⃣ IncomeRecord (Binary engine)
    # --------------------------------------------------
    record, _ = IncomeRecord.objects.get_or_create(
        member=placement,
        date=run_date,
        type="binary_engine",
    )

    # 🔹 Ensure eligibility unlock day binary income = 0
    binary_income_value = result.get("binary_income", Decimal("0.00"))
    if eligibility_today:
        binary_income_value = Decimal("0.00")

    record.binary_income = binary_income_value
    record.wallet_income = result.get("repurchase_wallet_bonus", Decimal("0.00"))
    record.eligibility_income = Decimal("0.00")  # 🔥 NEVER DUPLICATE
    record.sponsor_income = Decimal("0.00")      # 🔥 NEVER MIX
    record.total_income = record.binary_income + record.wallet_income

    # Optional: store audit fields
    record.binary_pairs = result.get("binary_pairs", 0)
    record.flashout_units = result.get("flashout_units", 0)
    record.save()


    # --------------------------------------------------
    # 8️⃣ DailyIncomeReport update (binary + wallet only)
    # --------------------------------------------------
    report, created = DailyIncomeReport.objects.get_or_create(
        member=placement,
        date=run_date,
        defaults={
            "eligibility_income": Decimal("0.00"),
            "binary_income": record.binary_income,
            "sponsor_income": Decimal("0.00"),
            "wallet_income": record.wallet_income,
            "salary_income": Decimal("0.00"),
            "total_income": record.binary_income + record.wallet_income,
        }
    )

    if not created:
        # 🔹 Respect eligibility unlock day
        if eligibility_today:
            report.binary_income = Decimal("0.00")
        else:
            report.binary_income = record.binary_income

        report.wallet_income = record.wallet_income   # ✅ overwrite instead of +=
        report.total_income = (
            report.eligibility_income +
            report.binary_income +
            report.sponsor_income +
            report.wallet_income +
            report.salary_income
        )
        report.save()

    print(f"✅ MLM Engine executed for {placement.auto_id} on {run_date}")



