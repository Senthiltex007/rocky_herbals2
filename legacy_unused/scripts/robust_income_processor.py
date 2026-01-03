# herbalapp/robust_income_processor.py
# ----------------------------------------------------------
# ✅ Robust MLM Income Processor
# ----------------------------------------------------------

from django.utils import timezone
from decimal import Decimal
from herbalapp.models import Member, IncomeRecord, BonusRecord, DailyIncomeReport

PAIR_VALUE = 500
ELIGIBILITY_BONUS = 500
DAILY_BINARY_PAIR_LIMIT = 5
FLASHOUT_UNIT_PAIRS = 5
FLASHOUT_UNIT_VALUE = 1000
MAX_FLASHOUT_UNITS_PER_DAY = 9

def process_member_income(member, run_date=None):
    run_date = run_date or timezone.now().date()

    # 1️⃣ Left / Right children counts
    left_children = Member.objects.filter(placement=member, side="left")
    right_children = Member.objects.filter(placement=member, side="right")
    left_total = member.left_cf + left_children.count()
    right_total = member.right_cf + right_children.count()

    # 2️⃣ Eligibility unlock
    became_eligible_today = False
    eligibility_income = 0
    if not member.binary_eligible:
        if (left_total >= 2 and right_total >= 1) or (left_total >= 1 and right_total >= 2):
            member.binary_eligible = True
            member.binary_eligible_since = run_date
            became_eligible_today = True
            eligibility_income = ELIGIBILITY_BONUS

            # Extra imbalance lock
            if left_total > right_total:
                member.left_locked = (left_total - right_total)
            else:
                member.right_locked = (right_total - left_total)

            # Mark sponsor eligibility flag
            member.has_completed_first_pair = True
            member.save(update_fields=[
                "binary_eligible", "binary_eligible_since",
                "left_locked", "right_locked", "has_completed_first_pair"
            ])

    # 3️⃣ Binary income
    new_pairs_today = min(left_children.count(), right_children.count())
    if became_eligible_today:
        new_pairs_today -= 1  # Unlock day first pair locked

    binary_pairs = max(min(new_pairs_today, DAILY_BINARY_PAIR_LIMIT), 0)
    binary_income = binary_pairs * PAIR_VALUE

    # 4️⃣ Flashout bonus
    extra_pairs = max(new_pairs_today - DAILY_BINARY_PAIR_LIMIT, 0)
    flashout_units = min(extra_pairs // FLASHOUT_UNIT_PAIRS, MAX_FLASHOUT_UNITS_PER_DAY)
    flashout_income = flashout_units * FLASHOUT_UNIT_VALUE
    washed_pairs = max(extra_pairs - (flashout_units * FLASHOUT_UNIT_PAIRS), 0)

    # 5️⃣ Carry forward
    member.left_cf = max(left_total - new_pairs_today, 0)
    member.right_cf = max(right_total - new_pairs_today, 0)
    member.save(update_fields=["left_cf", "right_cf"])

    # 6️⃣ Bonus Records
    if eligibility_income > 0:
        BonusRecord.objects.get_or_create(
            member=member, type="eligibility_bonus",
            amount=eligibility_income, date=run_date
        )
    if flashout_income > 0:
        BonusRecord.objects.get_or_create(
            member=member, type="flashout_bonus",
            amount=flashout_income, date=run_date
        )

    # 7️⃣ Sponsor income (Rules 1,2,3)
    sponsor_income_amount = Decimal("0.00")
    sponsor = member.sponsor
    parent = member.placement
    if sponsor:
        if parent and parent == sponsor:
            receiver = parent.parent
        else:
            receiver = sponsor

        # Rule 3: sponsor must have completed at least one 1:1 pair
        if receiver and getattr(receiver, "has_completed_first_pair", False):
            sponsor_income_amount = Decimal(eligibility_income + binary_income)

            report, created = DailyIncomeReport.objects.get_or_create(
                member=receiver,
                date=run_date,
                defaults={'sponsor_income': sponsor_income_amount}
            )
            if not created:
                report.sponsor_income += sponsor_income_amount
                report.save()

            receiver.total_sponsor_income += sponsor_income_amount
            receiver.save(update_fields=["total_sponsor_income"])

    # 8️⃣ IncomeRecord
    IncomeRecord.objects.get_or_create(
        member=member,
        date=run_date,
        defaults={
            "binary_income": binary_income,
            "sponsor_income": sponsor_income_amount,
            "flashout_units": flashout_units,
            "wallet_income": flashout_income,
            "washed_pairs": washed_pairs,
            "total_income": binary_income + sponsor_income_amount + flashout_income + eligibility_income
        }
    )

    return {
        "binary_income": binary_income,
        "eligibility_income": eligibility_income,
        "sponsor_income": sponsor_income_amount,
        "flashout_income": flashout_income,
        "flashout_units": flashout_units,
        "washed_pairs": washed_pairs,
    }

