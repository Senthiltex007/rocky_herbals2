# herbalapp/mlm_engine_binary_corrected.py

def calculate_member_binary_income_for_day(
    left_joins_today: int,
    right_joins_today: int,
    left_cf_before: int,
    right_cf_before: int,
    binary_eligible: bool,
):
    """
    Corrected Rocky Herbals MLM Binary Engine for ONE MEMBER for ONE DAY.

    Rules implemented:
    1️⃣ Lifetime eligibility: 1:2 or 2:1 only
    2️⃣ Before eligibility: all 1:1 or unpaired (2:0 / 0:2) → carry forward, no washout
    3️⃣ Eligibility bonus: ₹500 one-time
    4️⃣ Daily binary income: max 5 pairs (₹500/pair)
    5️⃣ Flashout bonus: 5 pairs → 1 unit (₹1000), max 9 units/day
    6️⃣ Washout: only applies after binary + flashout limit exceeded
    7️⃣ Carry forward: leftover single-side members
    """

    # -------------------------------
    # Constants
    # -------------------------------
    PAIR_VALUE = 500
    ELIGIBILITY_BONUS = 500
    DAILY_BINARY_PAIR_LIMIT = 5
    FLASHOUT_GROUP_SIZE = 5
    FLASHOUT_VALUE = 1000
    MAX_DAILY_FLASHOUTS = 9

    # -------------------------------
    # Total members including CF
    # -------------------------------
    L = left_joins_today + left_cf_before
    R = right_joins_today + right_cf_before

    new_binary_eligible = binary_eligible
    eligibility_income = 0
    binary_pairs_paid = 0
    binary_income = 0
    flashout_units = 0
    flashout_pairs_used = 0
    flashout_income = 0
    washed_pairs = 0

    # -------------------------------
    # 1️⃣ Eligibility check (1:2 or 2:1)
    # -------------------------------
    if not binary_eligible:
        if (L >= 1 and R >= 2) or (L >= 2 and R >= 1):
            # Eligible now
            new_binary_eligible = True
            eligibility_income = ELIGIBILITY_BONUS

            # Deduct eligibility pattern
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
            # ❌ Before eligibility → NO washout, just carry forward
            return {
                "new_binary_eligible": False,
                "eligibility_income": 0,
                "binary_pairs_paid": 0,
                "binary_income": 0,
                "flashout_units": 0,
                "flashout_pairs_used": 0,
                "flashout_income": 0,
                "washed_pairs": 0,
                "left_cf_after": L,
                "right_cf_after": R,
                "total_income": 0,
            }

    # -------------------------------
    # 2️⃣ After eligibility → only 1:1 counts
    # -------------------------------
    total_pairs_available = min(L, R)

    # -------------------------------
    # 3️⃣ Binary income: max 5 pairs/day
    # -------------------------------
    binary_pairs_paid = min(total_pairs_available, DAILY_BINARY_PAIR_LIMIT)
    binary_income = binary_pairs_paid * PAIR_VALUE
    L -= binary_pairs_paid
    R -= binary_pairs_paid

    # -------------------------------
    # 4️⃣ Flashout bonus
    # -------------------------------
    pairs_remaining_after_binary = total_pairs_available - binary_pairs_paid
    possible_flashout_units = pairs_remaining_after_binary // FLASHOUT_GROUP_SIZE
    flashout_units = min(possible_flashout_units, MAX_DAILY_FLASHOUTS)
    flashout_pairs_used = flashout_units * FLASHOUT_GROUP_SIZE
    flashout_income = flashout_units * FLASHOUT_VALUE
    L -= flashout_pairs_used
    R -= flashout_pairs_used

    # -------------------------------
    # 5️⃣ Washout (only excess pairs beyond binary + flashout)
    # -------------------------------
    pairs_remaining_after_flashout = pairs_remaining_after_binary - flashout_pairs_used
    washed_pairs = pairs_remaining_after_flashout
    L -= washed_pairs
    R -= washed_pairs

    # -------------------------------
    # 6️⃣ Carry forward
    # -------------------------------
    left_cf_after = L
    right_cf_after = R

    # -------------------------------
    # 7️⃣ Total income
    # -------------------------------
    total_income = eligibility_income + binary_income + flashout_income

    return {
        "new_binary_eligible": new_binary_eligible,
        "eligibility_income": eligibility_income,
        "binary_pairs_paid": binary_pairs_paid,
        "binary_income": binary_income,
        "flashout_units": flashout_units,
        "flashout_pairs_used": flashout_pairs_used,
        "flashout_income": flashout_income,
        "washed_pairs": washed_pairs,
        "left_cf_after": left_cf_after,
        "right_cf_after": right_cf_after,
        "total_income": total_income,
    }

# herbalapp/mlm_engine_binary.py

def determine_rank_from_bv(total_bv):
    """
    Temporary stub to fix ImportError
    You can enhance rank logic later
    """
    if total_bv >= 100000:
        return "DIAMOND"
    elif total_bv >= 50000:
        return "GOLD"
    elif total_bv >= 10000:
        return "SILVER"
    return "NONE"

