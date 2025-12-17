from django.utils import timezone


def calculate_member_binary_income_for_day(
    left_joins_today: int,
    right_joins_today: int,
    left_cf_before: int,
    right_cf_before: int,
    binary_eligible: bool,
):
    """
    Rocky Herbals – FINAL Binary Engine (with flashout to repurchase wallet)

    Implements ALL confirmed rules:

    - Lifetime eligibility ONLY from 1:2 or 2:1 (NOT 1:1).
    - One-time eligibility bonus = 500.
    - After eligibility: 1:1 pairs only.
    - Daily binary income max: 5 pairs (5 * 500 = 2500) → cash income.
    - After 5 pairs: flashout bonuses (5 pairs = 1 flashout = 1000).
    - Max 9 flashout units/day (9 * 1000 = 9000).
    - Flashout bonus goes ONLY to repurchase wallet (NOT cash income).
    - Pairs above binary + flashout → washout (lost).
    - Carry forward: leftover single-side counts (L or R) stay forever.
    - Sponsor income is NOT calculated here, but this function returns
      child_total_for_sponsor for outer sponsor engine.
    """

    # -------------------------------
    # 0. Plan configuration constants
    # -------------------------------
    PAIR_VALUE = 500                 # ₹500 per binary 1:1 pair
    ELIGIBILITY_BONUS = 500          # One-time bonus on 1:2 or 2:1

    DAILY_BINARY_PAIR_LIMIT = 5      # Max 5 pairs/day for binary income

    FLASHOUT_GROUP_SIZE = 5          # 5 pairs → 1 flashout
    FLASHOUT_VALUE = 1000            # ₹1000 per flashout unit
    MAX_DAILY_FLASHOUTS = 9          # Max 9 flashouts/day

    # -------------------------------
    # 1. Compute total available legs
    # -------------------------------
    L = left_joins_today + left_cf_before
    R = right_joins_today + right_cf_before

    # Prepare outputs
    new_binary_eligible = binary_eligible
    eligibility_income = 0
    became_eligible_today = False

    binary_pairs = 0
    binary_income = 0

    flashout_units = 0
    flashout_pairs_used = 0
    # Flashout goes to repurchase wallet, not cash
    repurchase_wallet_bonus = 0

    washed_pairs = 0

    # -------------------------------
    # 2. Lifetime eligibility check
    # -------------------------------
    if not binary_eligible:
        # Check if today’s combined L/R (with CF) qualifies for 1:2 or 2:1
        if (L >= 1 and R >= 2) or (L >= 2 and R >= 1):
            new_binary_eligible = True
            became_eligible_today = True
            eligibility_income = ELIGIBILITY_BONUS

            # Deduct the eligibility pattern from L and R.
            # Strategy: keep sides as balanced as possible.
            if L >= 2 and R >= 2:
                if L > R:
                    # Left heavier → use 2:1
                    L -= 2
                    R -= 1
                else:
                    # Right heavier or equal → use 1:2
                    L -= 1
                    R -= 2
            else:
                if L >= 1 and R >= 2:
                    # 1:2 eligibility
                    L -= 1
                    R -= 2
                elif L >= 2 and R >= 1:
                    # 2:1 eligibility
                    L -= 2
                    R -= 1
        else:
            # Not yet eligible:
            # - All pairs formed today are washout (lost).
            # - Remaining singles are CF.
            potential_pairs_today = min(L, R)
            washed_pairs = potential_pairs_today

            # Remove washed pairs from both sides
            L -= washed_pairs
            R -= washed_pairs

            left_cf_after = L
            right_cf_after = R

            total_income = 0
            child_total_for_sponsor = total_income  # sponsor sees only cash income

            return {
                "new_binary_eligible": new_binary_eligible,      # still False
                "became_eligible_today": False,
                "eligibility_income": 0,
                "binary_pairs": 0,
                "binary_income": 0,
                "flashout_units": 0,
                "flashout_pairs_used": 0,
                "repurchase_wallet_bonus": 0,
                "washed_pairs": washed_pairs,
                "left_cf_after": left_cf_after,
                "right_cf_after": right_cf_after,
                "total_income": total_income,
                "child_total_for_sponsor": child_total_for_sponsor,
            }

    # -------------------------------
    # 3. After eligibility: only 1:1 pairs count
    # -------------------------------
    total_pairs_available = min(L, R)

    # -------------------------------
    # 4. First layer: Binary income (max 5 pairs)
    # -------------------------------
    binary_pairs = min(total_pairs_available, DAILY_BINARY_PAIR_LIMIT)
    binary_income = binary_pairs * PAIR_VALUE

    pairs_remaining_after_binary = total_pairs_available - binary_pairs

    # Remove used pairs from L & R
    L -= binary_pairs
    R -= binary_pairs

    # -------------------------------
    # 5. Second layer: Flashout bonuses (to repurchase wallet)
    # -------------------------------
    possible_flashout_units = pairs_remaining_after_binary // FLASHOUT_GROUP_SIZE
    flashout_units = min(possible_flashout_units, MAX_DAILY_FLASHOUTS)

    flashout_pairs_used = flashout_units * FLASHOUT_GROUP_SIZE
    # Flashout bonus goes ONLY to repurchase wallet, NOT to cash income
    repurchase_wallet_bonus = flashout_units * FLASHOUT_VALUE

    pairs_remaining_after_flashout = pairs_remaining_after_binary - flashout_pairs_used

    # Remove flashout pairs from L & R
    L -= flashout_pairs_used
    R -= flashout_pairs_used

    # -------------------------------
    # 6. Third layer: Washout
    # -------------------------------
    washed_pairs = pairs_remaining_after_flashout

    L -= washed_pairs
    R -= washed_pairs

    # -------------------------------
    # 7. Carry forward
    # -------------------------------
    left_cf_after = L
    right_cf_after = R

    # -------------------------------
    # 8. Total cash income for the day
    # -------------------------------
    # total_income = eligibility + binary ONLY.
    # Flashout does NOT come to cash; it goes to repurchase wallet.
    total_income = eligibility_income + binary_income

    # For sponsor engine: sponsor income is based on CASH income only
    child_total_for_sponsor = total_income

    return {
        "new_binary_eligible": new_binary_eligible,          # bool
        "became_eligible_today": became_eligible_today,      # eligibility happened today?
        "eligibility_income": eligibility_income,            # ₹ cash
        "binary_pairs": binary_pairs,                        # count
        "binary_income": binary_income,                      # ₹ cash
        "flashout_units": flashout_units,                    # count of 1000₹ units to repurchase
        "flashout_pairs_used": flashout_pairs_used,          # pairs used for flashout
        "repurchase_wallet_bonus": repurchase_wallet_bonus,  # ₹ to repurchase wallet
        "washed_pairs": washed_pairs,                        # pairs lost
        "left_cf_after": left_cf_after,                      # count
        "right_cf_after": right_cf_after,                    # count
        "total_income": total_income,                        # ₹ cash (eligibility + binary)
        "child_total_for_sponsor": child_total_for_sponsor,  # sponsor sees only cash
    }
def determine_rank_from_bv(bv: int):
    """
    Returns:
        (rank_title, monthly_salary, months)
        or None if no rank achieved.

    Rocky Herbals BV Rank Slabs (Option A – Monthly salary):

    - 25 Cr  → Top Tier        → 10,00,000 × 3 months
    - 10 Cr  → Triple Diamond  → 5,00,000 × 4 months
    - 5 Cr   → Double Diamond  → 2,00,000 × 6 months
    - 2.5 Cr → Diamond Star    → 1,00,000 × 8 months
    - 1 Cr   → Mono Platinum   → 50,000 × 10 months
    - 50 L   → Platinum Star   → 20,000 × 12 months
    - 25 L   → Gilded Gold     → 10,000 × 10 months
    - 10 L   → Gold Star       → 5,000 × 8 months
    - 5 L    → Shine Silver    → 2,500 × 6 months
    - 2.5 L  → Triple Star     → 1,000 × 5 months
    - 1 L    → Double Star     → 500 × 4 months
    - 50 K   → 1st Star        → 300 × 3 months
    """

    # 25 Cr
    if bv >= 250000000:
        return ("Top Tier", 1000000, 3)

    # 10 Cr
    if bv >= 100000000:
        return ("Triple Diamond", 500000, 4)

    # 5 Cr
    if bv >= 50000000:
        return ("Double Diamond", 200000, 6)

    # 2.5 Cr
    if bv >= 25000000:
        return ("Diamond Star", 100000, 8)

    # 1 Cr
    if bv >= 10000000:
        return ("Mono Platinum", 50000, 10)

    # 50 Lakh
    if bv >= 5000000:
        return ("Platinum Star", 20000, 12)

    # 25 Lakh
    if bv >= 2500000:
        return ("Gilded Gold", 10000, 10)

    # 10 Lakh
    if bv >= 1000000:
        return ("Gold Star", 5000, 8)

    # 5 Lakh
    if bv >= 500000:
        return ("Shine Silver", 2500, 6)

    # 2.5 Lakh
    if bv >= 250000:
        return ("Triple Star", 1000, 5)

    # 1 Lakh
    if bv >= 100000:
        return ("Double Star", 500, 4)

    # 50,000
    if bv >= 50000:
        return ("1st Star", 300, 3)

    return None

