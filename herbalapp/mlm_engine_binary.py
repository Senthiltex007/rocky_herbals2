from django.utils import timezone
from herbalapp.models import BonusRecord

PAIR_VALUE = 500
ELIGIBILITY_BONUS = 500
DAILY_BINARY_PAIR_LIMIT = 5

FLASHOUT_UNIT_PAIRS = 5       # 5 new pairs = 1 unit
FLASHOUT_UNIT_VALUE = 1000
MAX_FLASHOUT_UNITS_PER_DAY = 9

def calculate_member_binary_income_for_day(
    *,
    left_joins_today: int,
    right_joins_today: int,
    left_cf_before: int,
    right_cf_before: int,
    binary_eligible: bool,
    member,
    run_date
):
    """
    Rules:
    - Eligibility (lifetime) when totals (CF + today) reach 1:2 or 2:1 → ₹500 once.
    - On unlock day: first pair locked (no binary income), one extra unpaired locked.
    - After eligibility: only today's new 1:1 pairs count for binary income; cap 5/day.
    - Flashout: extra new pairs (beyond 5) → 5 pairs = 1 unit = ₹1000; cap 9 units/day; leftover → washout.
    - Carry-forward: unmatched totals persist; consume only today's matched pairs.
    - Sponsor income: child_total_for_sponsor = eligibility_income (if unlocked today) + binary_income (today).
    """

    left_joins_today = int(left_joins_today or 0)
    right_joins_today = int(right_joins_today or 0)
    L_total = int(left_cf_before or 0) + left_joins_today
    R_total = int(right_cf_before or 0) + right_joins_today

    eligibility_income = 0
    became_eligible_today = False
    binary_income = 0
    flashout_units = 0
    repurchase_wallet_bonus = 0
    washed_pairs = 0

    # 1) Eligibility unlock
    if not bool(binary_eligible):
        cond_21 = (L_total >= 2 and R_total >= 1)
        cond_12 = (L_total >= 1 and R_total >= 2)
        if cond_21 or cond_12:
            eligibility_income = ELIGIBILITY_BONUS
            became_eligible_today = True
            member.binary_eligible = True
            member.binary_eligible_since = run_date
            if hasattr(member, "has_completed_first_pair"):
                member.has_completed_first_pair = True
            member.save(update_fields=["binary_eligible", "binary_eligible_since"] + (["has_completed_first_pair"] if hasattr(member, "has_completed_first_pair") else []))

            # First pair locked, no binary income
            locked_pairs = 1
            effective_pairs = min(left_joins_today, right_joins_today) - locked_pairs
            if effective_pairs > 0:
                if effective_pairs > DAILY_BINARY_PAIR_LIMIT:
                    binary_income = DAILY_BINARY_PAIR_LIMIT * PAIR_VALUE
                else:
                    binary_income = effective_pairs * PAIR_VALUE

    else:
        # Already eligible → count all new 1:1 pairs
        pairs_today = min(left_joins_today, right_joins_today)
        if pairs_today > DAILY_BINARY_PAIR_LIMIT:
            binary_income = DAILY_BINARY_PAIR_LIMIT * PAIR_VALUE
        else:
            binary_income = pairs_today * PAIR_VALUE

    # Flashout bonus
    extra_pairs_today = max(min(left_joins_today, right_joins_today) - DAILY_BINARY_PAIR_LIMIT, 0)
    flashout_units = min(extra_pairs_today // FLASHOUT_UNIT_PAIRS, MAX_FLASHOUT_UNITS_PER_DAY)
    repurchase_wallet_bonus = flashout_units * FLASHOUT_UNIT_VALUE
    covered_by_flashout = flashout_units * FLASHOUT_UNIT_PAIRS
    washed_pairs = max(extra_pairs_today - covered_by_flashout, 0)

    # Carry-forward
    left_cf_after = max(L_total - min(left_joins_today, right_joins_today), 0)
    right_cf_after = max(R_total - min(left_joins_today, right_joins_today), 0)

    child_total_for_sponsor = eligibility_income + binary_income
    total_income = eligibility_income + binary_income + repurchase_wallet_bonus

    # ✅ Removed direct IncomeRecord save here
    # Monitor will handle saving IncomeRecord centrally

    # BonusRecord logs
    if eligibility_income > 0:
        BonusRecord.objects.create(member=member, type="eligibility_bonus", amount=eligibility_income)
    if repurchase_wallet_bonus > 0:
        BonusRecord.objects.create(member=member, type="flashout_bonus", amount=repurchase_wallet_bonus)

    return {
        "became_eligible_today": became_eligible_today,
        "eligibility_income": eligibility_income,
        "binary_income": binary_income,
        "flashout_units": flashout_units,
        "repurchase_wallet_bonus": repurchase_wallet_bonus,
        "washed_pairs": washed_pairs,
        "binary_eligible": member.binary_eligible,
        "left_cf_after": left_cf_after,
        "right_cf_after": right_cf_after,
        "child_total_for_sponsor": child_total_for_sponsor,
        "total_income": total_income,
    }

