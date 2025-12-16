from django.utils import timezone


def calculate_member_binary_income_for_day(
    left_joins_today: int,
    right_joins_today: int,
    left_cf_before: int,
    right_cf_before: int,
    binary_eligible: bool,
):
    """
    Core MLM binary engine for ONE MEMBER for ONE DAY.

    Implements ALL rules:
    - Lifetime eligibility from 1:2 or 2:1 (NOT 1:1)
    - One-time eligibility bonus = 500
    - After eligibility: only 1:1 pairs
    - Daily binary income max: 5 pairs (5 * 500 = 2500)
    - After 5 pairs: flashout bonuses (5 pairs = 1 flashout = 1000)
    - Max 9 flashout bonuses per day (9 * 1000 = 9000)
    - Extra pairs (above binary + flashout) → washout (lost)
    - Carry forward: leftover single side counts (not forming pairs) stay forever
    """

    # -------------------------------
    # 0. Plan configuration constants
    # -------------------------------
    PAIR_VALUE = 500                 # ₹500 per 1:1 pair
    ELIGIBILITY_BONUS = 500          # One-time bonus on 1:2 or 2:1
    DAILY_BINARY_PAIR_LIMIT = 5      # Max 5 pairs/day for binary income
    FLASHOUT_GROUP_SIZE = 5          # 5 pairs → 1 flashout
    FLASHOUT_VALUE = 1000            # ₹1000 per flashout
    MAX_DAILY_FLASHOUTS = 9          # Max 9 flashouts/day

    # -------------------------------
    # 1. Compute total available legs
    # -------------------------------
    # Today’s total effective left & right counts including CF
    L = left_joins_today + left_cf_before
    R = right_joins_today + right_cf_before

    # Prepare outputs
    new_binary_eligible = binary_eligible
    eligibility_income = 0

    binary_pairs_paid = 0
    binary_income = 0

    flashout_pairs_used = 0
    flashout_units = 0
    flashout_income = 0

    washed_pairs = 0

    # -------------------------------
    # 2. Lifetime eligibility check
    # -------------------------------
    # Eligibility ONLY from 1:2 or 2:1, NOT 1:1
    # This can happen only once in member lifetime.
    # NOTE: This engine only returns new_binary_eligible flag.
    # Saving binary_eligible_date must be done OUTSIDE this function,
    # where the Member instance is available.
    if not binary_eligible:
        # Check if today’s combined L/R (with CF) qualifies for 1:2 or 2:1
        if (L >= 1 and R >= 2) or (L >= 2 and R >= 1):
            new_binary_eligible = True
            eligibility_income = ELIGIBILITY_BONUS

            # Deduct the eligibility pattern from L and R.
            # IMPORTANT: We must preserve as many total pairs as possible.
            # Strategy: Prefer the pattern that leaves the larger min(L, R) afterwards.
            # If both 1:2 and 2:1 are possible, choose the one where the side with more
            # members spends 2, to make sides more balanced.

            if L >= 2 and R >= 2:
                # Both 1:2 and 2:1 possible; choose based on which side is heavier
                if L > R:
                    # Use 2:1 (spend 2 from left, 1 from right)
                    L -= 2
                    R -= 1
                else:
                    # Use 1:2 (spend 1 from left, 2 from right)
                    L -= 1
                    R -= 2
            else:
                # Only one pattern possible, pick that
                if L >= 1 and R >= 2:
                    # 1:2 eligibility
                    L -= 1
                    R -= 2
                elif L >= 2 and R >= 1:
                    # 2:1 eligibility
                    L -= 2
                    R -= 1
                # No else, because we already checked the OR condition above
        else:
            # Not yet eligible → ALL PAIRS TODAY ARE WASHOUT
            # IMPORTANT:
            # - Pairs formed today, while not eligible, are lost (washout)
            # - Single-side excess remains as CF.
            potential_pairs_today = min(L, R)
            washed_pairs = potential_pairs_today

            # Remove washed pairs from both sides
            L -= washed_pairs
            R -= washed_pairs

            # Remaining L/R become CF
            left_cf_after = L
            right_cf_after = R

            # No binary income, no flashout, no eligibility bonus
            total_income = 0

            return {
                "new_binary_eligible": new_binary_eligible,
                "eligibility_income": eligibility_income,
                "binary_pairs_paid": 0,
                "binary_income": 0,
                "flashout_units": 0,
                "flashout_pairs_used": 0,
                "flashout_income": 0,
                "washed_pairs": washed_pairs,
                "left_cf_after": left_cf_after,
                "right_cf_after": right_cf_after,
                "total_income": total_income,
                # Sponsor / rank handled outside
            }

    # -------------------------------
    # 3. After eligibility: only 1:1 pairs count
    # -------------------------------
    # At this point, member is eligible (either already, or became so above).
    # All remaining pairs form 1:1 pairs.
    total_pairs_available = min(L, R)

    # -------------------------------
    # 4. First layer: Binary income (max 5 pairs)
    # -------------------------------
    binary_pairs_paid = min(total_pairs_available, DAILY_BINARY_PAIR_LIMIT)
    binary_income = binary_pairs_paid * PAIR_VALUE

    pairs_remaining_after_binary = total_pairs_available - binary_pairs_paid

    # Remove used pairs from L & R
    L -= binary_pairs_paid
    R -= binary_pairs_paid

    # -------------------------------
    # 5. Second layer: Flashout bonuses
    # -------------------------------
    # Each flashout consumes FLASHOUT_GROUP_SIZE pairs
    # Max MAX_DAILY_FLASHOUTS per day
    possible_flashout_units = pairs_remaining_after_binary // FLASHOUT_GROUP_SIZE
    flashout_units = min(possible_flashout_units, MAX_DAILY_FLASHOUTS)

    flashout_pairs_used = flashout_units * FLASHOUT_GROUP_SIZE
    flashout_income = flashout_units * FLASHOUT_VALUE

    pairs_remaining_after_flashout = pairs_remaining_after_binary - flashout_pairs_used

    # Remove flashout pairs from L & R
    L -= flashout_pairs_used
    R -= flashout_pairs_used

    # -------------------------------
    # 6. Third layer: Washout
    # -------------------------------
    # Any remaining full pairs (1:1) after:
    # - 5 binary pairs
    # - up to 9 flashout units
    # are WASHOUT (lost).
    washed_pairs = pairs_remaining_after_flashout

    # Remove washed pairs from L & R
    L -= washed_pairs
    R -= washed_pairs

    # -------------------------------
    # 7. Carry forward
    # -------------------------------
    # Leftover single side members (L or R) stay as CF.
    left_cf_after = L
    right_cf_after = R

    # -------------------------------
    # 8. Total income for the day
    # -------------------------------
    total_income = eligibility_income + binary_income + flashout_income

    # NOTE:
    # - Sponsor income is NOT calculated here, because this function
    #   doesn't know the Member or sponsor object.
    # - Sponsor logic (including ONE-TIME 1:1 achievement) is handled
    #   in the engine runner where Member and sponsor are available.

    return {
        "new_binary_eligible": new_binary_eligible,  # bool
        "eligibility_income": eligibility_income,    # ₹
        "binary_pairs_paid": binary_pairs_paid,      # count
        "binary_income": binary_income,              # ₹
        "flashout_units": flashout_units,            # count of 1000₹ units
        "flashout_pairs_used": flashout_pairs_used,  # pairs used for flashout
        "flashout_income": flashout_income,          # ₹
        "washed_pairs": washed_pairs,                # pairs lost
        "left_cf_after": left_cf_after,              # count
        "right_cf_after": right_cf_after,            # count
        "total_income": total_income,                # ₹
    }


# -----------------------------
# CORRECT ROCKY HERBALS RANK LOGIC
# -----------------------------
def determine_rank_from_bv(bv: int):
    """
    Returns:
        (rank_title, monthly_salary, months)
        or None if no rank achieved
    """

    # 25 Cr
    if bv >= 250000000:
        return ("Top Tier", 10000000, 3)

    # 10 Cr
    if bv >= 100000000:
        return ("Triple Diamond", 5000000, 4)

    # 5 Cr
    if bv >= 50000000:
        return ("Double Diamond", 2000000, 6)

    # 2.5 Cr
    if bv >= 25000000:
        return ("Diamond Star", 1000000, 8)

    # 1 Cr
    if bv >= 10000000:
        return ("Mono Platinum", 500000, 10)

    # 50 Lakh
    if bv >= 5000000:
        return ("Platinum Star", 200000, 12)

    # 25 Lakh
    if bv >= 2500000:
        return ("Gilded Gold", 100000, 10)

    # 10 Lakh
    if bv >= 1000000:
        return ("Gold Star", 50000, 8)

    # 5 Lakh
    if bv >= 500000:
        return ("Shine Silver", 25000, 6)

    # 2.5 Lakh
    if bv >= 250000:
        return ("Triple Star", 10000, 5)

    # 1 Lakh
    if bv >= 100000:
        return ("Double Star", 5000, 4)

    # 50,000
    if bv >= 50000:
        return ("1st Star", 3000, 3)

    return None

