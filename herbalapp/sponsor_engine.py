# herbalapp/mlm_engine_full.py

from datetime import date
from decimal import Decimal
from herbalapp.models import Member, IncomeRecord, SponsorIncome, DailyIncomeReport
from herbalapp.sponsor_engine import process_sponsor_income

receiver = resolve_sponsor_receiver(child_member)

if is_dummy_root(receiver):
    return None

# ------------------------------
# Constants
# ------------------------------
PAIR_VALUE = 500
ELIGIBILITY_BONUS = 500
DAILY_BINARY_PAIR_LIMIT = 5
FLASHOUT_GROUP_SIZE = 5
FLASHOUT_VALUE = 1000
MAX_DAILY_FLASHOUTS = 9

# ------------------------------
# Main MLM daily processor
# ------------------------------
def process_member_daily_income(member: Member, today: date = None):
    """
    Processes ONE member's daily income:
    1. Binary eligibility
    2. Binary income (max 5 pairs/day)
    3. Flashout (max 9 units/day)
    4. Washout (excess beyond binary+flashout)
    5. Carry forward (unpaired)
    6. Sponsor income
    """
    if not today:
        today = date.today()

    # Skip dummy root
    if member.auto_id == "rocky004":
        return None

    # CF from previous day
    left_cf_before = member.left_cf or 0
    right_cf_before = member.right_cf or 0

    # Today's new members under left/right
    left_today = member.left_today or 0
    right_today = member.right_today or 0

    binary_eligible = member.binary_eligible

    # ------------------------------
    # 1️⃣ Eligibility check (1:2 / 2:1)
    # ------------------------------
    L = left_today + left_cf_before
    R = right_today + right_cf_before
    new_binary_eligible = binary_eligible
    eligibility_income = 0

    if not binary_eligible:
        if (L >= 1 and R >= 2) or (L >= 2 and R >= 1):
            # Become eligible
            new_binary_eligible = True
            eligibility_income = ELIGIBILITY_BONUS

            if L >= 2 and R >= 2:
                if L > R:
                    L -= 2
                    R -= 1
                else:
                    L -= 1
                    R -= 2
            elif L >= 1 and R >= 2:
                L -= 1
                R -= 2
            elif L >= 2 and R >= 1:
                L -= 2
                R -= 1
        else:
            # ❌ Pre-eligibility → carry forward only
            member.left_cf = L
            member.right_cf = R
            member.save(update_fields=["left_cf", "right_cf"])
            return {
                "binary_income": 0,
                "eligibility_income": 0,
                "flashout_income": 0,
                "washed_pairs": 0,
                "left_cf_after": L,
                "right_cf_after": R,
                "total_income": 0,
            }

    # ------------------------------
    # 2️⃣ Binary income (1:1 pairs)
    # ------------------------------
    total_pairs = min(L, R)
    binary_pairs_paid = min(total_pairs, DAILY_BINARY_PAIR_LIMIT)
    binary_income = binary_pairs_paid * PAIR_VALUE
    L -= binary_pairs_paid
    R -= binary_pairs_paid

    # ------------------------------
    # 3️⃣ Flashout
    # ------------------------------
    remaining_pairs = total_pairs - binary_pairs_paid
    flashout_units = min(remaining_pairs // FLASHOUT_GROUP_SIZE, MAX_DAILY_FLASHOUTS)
    flashout_pairs_used = flashout_units * FLASHOUT_GROUP_SIZE
    flashout_income = flashout_units * FLASHOUT_VALUE
    L -= flashout_pairs_used
    R -= flashout_pairs_used

    # ------------------------------
    # 4️⃣ Washout (only excess beyond binary + flashout)
    # ------------------------------
    pairs_remaining_after_flashout = remaining_pairs - flashout_pairs_used
    washed_pairs = pairs_remaining_after_flashout
    L -= washed_pairs
    R -= washed_pairs

    # ------------------------------
    # 5️⃣ Carry forward
    # ------------------------------
    member.left_cf = L
    member.right_cf = R
    member.binary_eligible = new_binary_eligible
    member.save(update_fields=["left_cf", "right_cf", "binary_eligible"])

    # ------------------------------
    # 6️⃣ Total income
    # ------------------------------
    total_income = eligibility_income + binary_income + flashout_income

    # ------------------------------
    # 7️⃣ Update IncomeRecord
    # ------------------------------
    rec, _ = IncomeRecord.objects.get_or_create(
        member=member,
        created_at=today,
        defaults={
            "eligibility_income": Decimal(eligibility_income),
            "binary_income": Decimal(binary_income),
            "sponsor_income": Decimal(0),
            "wallet_income": Decimal(0),
            "salary_income": Decimal(0),
            "total_income": Decimal(total_income),
            "binary_pairs": binary_pairs_paid,
        }
    )
    if rec:
        rec.eligibility_income = Decimal(eligibility_income)
        rec.binary_income = Decimal(binary_income)
        rec.total_income = Decimal(total_income)
        rec.binary_pairs = binary_pairs_paid
        rec.save()

    # ------------------------------
    # 8️⃣ Sponsor income (if child became eligible today)
    # ------------------------------
    sponsor_income_amount = 0
    if eligibility_income > 0:
        sponsor_income_amount = process_sponsor_income(
            child_member=member,
            run_date=today,
            child_became_eligible_today=True
        )

    return {
        "binary_income": binary_income,
        "eligibility_income": eligibility_income,
        "flashout_income": flashout_income,
        "washed_pairs": washed_pairs,
        "left_cf_after": L,
        "right_cf_after": R,
        "total_income": total_income,
        "sponsor_income": sponsor_income_amount,
    }

