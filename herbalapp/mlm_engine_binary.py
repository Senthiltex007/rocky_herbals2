# herbalapp/mlm_engine_binary.py

def calculate_member_binary_income_for_day(
    left_joins_today: int,
    right_joins_today: int,
    left_cf_before: int,
    right_cf_before: int,
    binary_eligible: bool,
):
    """
    FINAL Rocky Herbals MLM Binary Engine (Rule-Accurate)

    RULES IMPLEMENTED:
    1️⃣ Binary eligibility (lifetime): 1:2 or 2:1
    2️⃣ Before eligibility: NO income, NO washout, only carry forward
    3️⃣ Eligibility bonus: ₹500 (one-time only)
    4️⃣ Eligibility day: eligibility pair NOT counted as binary pair
    5️⃣ Daily binary income: max 5 pairs/day (₹500 per pair)
    6️⃣ Flashout bonus: 5 pairs = 1 unit (₹1000), max 9 units/day
    7️⃣ Flashout → repurchase wallet only
    8️⃣ Washout: excess pairs beyond binary + flashout
    9️⃣ Carry forward: lifetime, waits until matched
    """

    # -------------------------------
    # CONSTANTS
    # -------------------------------
    PAIR_VALUE = 500
    ELIGIBILITY_BONUS = 500
    DAILY_BINARY_PAIR_LIMIT = 5
    FLASHOUT_GROUP_SIZE = 5
    FLASHOUT_VALUE = 1000
    MAX_DAILY_FLASHOUTS = 9

    # -------------------------------
    # TOTAL MEMBERS (TODAY + CF)
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
    # 1️⃣ BINARY ELIGIBILITY CHECK
    # -------------------------------
    if not binary_eligible:
        if (L >= 1 and R >= 2) or (L >= 2 and R >= 1):
            new_binary_eligible = True
            eligibility_income = ELIGIBILITY_BONUS

            # Deduct eligibility pair from counts
            if L >= 1 and R >= 2:
                L -= 1
                R -= 2
            elif L >= 2 and R >= 1:
                L -= 2
                R -= 1

            # -------------------------------
            # Eligibility day → allow binary income up to 4 pairs
            # -------------------------------
            total_pairs_available = min(L, R)
            binary_pairs_paid = min(total_pairs_available, 4)  # max 4 pairs on eligibility day
            binary_income = binary_pairs_paid * PAIR_VALUE

            # Deduct binary pairs used
            L -= binary_pairs_paid
            R -= binary_pairs_paid

            # -------------------------------
            # Flashout from remaining pairs after binary pairs
            # -------------------------------
            pairs_remaining_after_binary = total_pairs_available - binary_pairs_paid
            possible_flashout_units = pairs_remaining_after_binary // FLASHOUT_GROUP_SIZE
            flashout_units = min(possible_flashout_units, MAX_DAILY_FLASHOUTS)
            flashout_pairs_used = flashout_units * FLASHOUT_GROUP_SIZE
            flashout_income = flashout_units * FLASHOUT_VALUE

            # Deduct flashout pairs
            L -= flashout_pairs_used
            R -= flashout_pairs_used

            # Washout
            washed_pairs = pairs_remaining_after_binary - flashout_pairs_used

            # Total income for the day = eligibility + binary + flashout
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
                "left_cf_after": L,
                "right_cf_after": R,
                "total_income": total_income,
            }

    # -------------------------------
    # 2️⃣ AFTER ELIGIBILITY → ONLY 1:1 PAIRS
    # -------------------------------
    total_pairs_available = min(L, R)

    # -------------------------------
    # 3️⃣ DAILY BINARY INCOME
    # -------------------------------
    binary_pairs_paid = min(total_pairs_available, DAILY_BINARY_PAIR_LIMIT)
    binary_income = binary_pairs_paid * PAIR_VALUE

    L -= binary_pairs_paid
    R -= binary_pairs_paid

    # -------------------------------
    # 4️⃣ FLASHOUT BONUS
    # -------------------------------
    pairs_remaining_after_binary = total_pairs_available - binary_pairs_paid

    possible_flashout_units = pairs_remaining_after_binary // FLASHOUT_GROUP_SIZE
    flashout_units = min(possible_flashout_units, MAX_DAILY_FLASHOUTS)

    flashout_pairs_used = flashout_units * FLASHOUT_GROUP_SIZE
    flashout_income = flashout_units * FLASHOUT_VALUE

    L -= flashout_pairs_used
    R -= flashout_pairs_used

    # -------------------------------
    # 5️⃣ WASHOUT (EXCESS PAIRS)
    # -------------------------------
    pairs_remaining_after_flashout = pairs_remaining_after_binary - flashout_pairs_used
    washed_pairs = pairs_remaining_after_flashout

    L -= washed_pairs
    R -= washed_pairs

    # -------------------------------
    # 6️⃣ CARRY FORWARD
    # -------------------------------
    left_cf_after = L
    right_cf_after = R

    # -------------------------------
    # 7️⃣ TOTAL INCOME
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


# -------------------------------------------------
# TEMP RANK FUNCTION (SAFE STUB)
# -------------------------------------------------
def determine_rank_from_bv(total_bv):
    if total_bv >= 100000:
        return "DIAMOND"
    elif total_bv >= 50000:
        return "GOLD"
    elif total_bv >= 10000:
        return "SILVER"
    return "NONE"
