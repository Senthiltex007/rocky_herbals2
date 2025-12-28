# herbalapp/test_engine.py
# ----------------------------------------------------------
# Test Engine for FINAL MASTER MLM RULE SYSTEM + Sponsor Income
# ----------------------------------------------------------

def test_engine(
    L_today,
    R_today,
    cf_left=0,
    cf_right=0,
    binary_eligible=False,
    lifetime_pairs=0,
    eligibility_unlocked_today=False,
    placement_id=None,
    sponsor_id=None,
    sponsor_has_pair=False,  # Rule 3: sponsor already has 1:1 (binary eligible)
):
    # --------------------------------------------
    # Step 0: Combine today + carry forward
    # --------------------------------------------
    L = L_today + cf_left
    R = R_today + cf_right

    # --------------------------------------------
    # Initialize outputs
    # --------------------------------------------
    eligibility_bonus = 0
    binary_cash = 0
    flash_units = 0
    repurchase_amount = 0
    washout_pairs = 0
    sponsor_income = 0
    sponsor_income_target = None
    credited_pairs = 0
    base_pairs = 0  # safe default for later audit use

    # --------------------------------------------
    # Boolean helpers
    # --------------------------------------------
    can_unlock_today = (not binary_eligible) and (
        (L >= 1 and R >= 2) or (L >= 2 and R >= 1)
    )
    unlocked_today = False
    can_pay_binary_today = False
    cap_4_pairs_today = False
    cap_5_pairs_today = False
    has_excess_for_flashout = False
    has_washout = False
    has_carry_forward = False
    unlock_day_cap_reached = False
    unlock_day_binary_corrected = False
    unlock_pair_income_excluded = False  # audit: unlock structure income excluded

    # --------------------------------------------
    # Rule 1: Binary Eligibility Unlock (1:2 or 2:1)
    # --------------------------------------------
    if can_unlock_today:
        binary_eligible = True
        eligibility_unlocked_today = True
        unlocked_today = True
        eligibility_bonus = 500
        lifetime_pairs += 1  # unlock pair counted once

        # consume unlock structure (either 1:2 or 2:1)
        if L >= 1 and R >= 2:
            L -= 1
            R -= 2
        else:
            L -= 2
            R -= 1
        unlock_pair_income_excluded = True

    # --------------------------------------------
    # Rule 2: Binary Income (fresh 1:1 after unlock consumption)
    # --------------------------------------------
    if binary_eligible:
        base_pairs = min(L, R)
        credited_pairs = min(base_pairs, 5)
        binary_cash = credited_pairs * 500
        lifetime_pairs += credited_pairs
        cap_5_pairs_today = (credited_pairs == 5)

        # consume credited pairs
        L -= credited_pairs
        R -= credited_pairs

        can_pay_binary_today = (credited_pairs > 0)

        # audit flags
        if eligibility_unlocked_today:
            unlock_pair_income_excluded = True
            unlock_day_cap_reached = (credited_pairs == 5)
            unlock_day_binary_corrected = True

    # --------------------------------------------
    # Rule 3: Eligibility Bonus validity
    # --------------------------------------------
    if eligibility_unlocked_today:
        eligibility_bonus = 500
    else:
        eligibility_bonus = 0

    # --------------------------------------------
    # Rule 4: Flashout (blocks of 5 pairs, max 9 units)
    # --------------------------------------------
    remaining_pairs = min(L, R)
    has_excess_for_flashout = remaining_pairs >= 5
    if has_excess_for_flashout:
        flash_units = min(remaining_pairs // 5, 9)
        repurchase_amount = flash_units * 1000
        L -= flash_units * 5
        R -= flash_units * 5

    # --------------------------------------------
    # Rule 5: Washout (leftover equal pairs after flashout)
    # --------------------------------------------
    leftover_pairs_after_flashout = min(L, R)
    has_washout = leftover_pairs_after_flashout > 0
    if has_washout:
        washout_pairs = leftover_pairs_after_flashout
        L -= washout_pairs
        R -= washout_pairs

    # --------------------------------------------
    # Rule 6: Carry Forward
    # --------------------------------------------
    cf_left, cf_right = L, R
    has_carry_forward = (cf_left > 0 or cf_right > 0)

    # --------------------------------------------
    # Rule 7: Sponsor Income (as per your 3 rules)
    # --------------------------------------------
    # Rule 1 & 2: decide target
    if placement_id is not None and sponsor_id is not None:
        if placement_id == sponsor_id:
            sponsor_income_target = f"parent_of_{placement_id}"
        else:
            sponsor_income_target = sponsor_id

    # Rule 3: credit only if sponsor already has 1:1 pair (binary eligible)
    # Formula: sponsor income = child eligibility bonus (500 if unlocked today) + child binary cash (today)
    if sponsor_income_target and sponsor_has_pair:
        sponsor_income = eligibility_bonus + binary_cash
    else:
        sponsor_income = 0  # not eligible or no target

    # --------------------------------------------
    # Extra audit booleans (define before return)
    # --------------------------------------------
    unlock_pair_income_blocked = eligibility_unlocked_today and (binary_cash >= 0)
    unlock_day_pairs_capped = eligibility_unlocked_today and (credited_pairs == 3)
    # guard: use base_pairs safely (defined default 0)
    unlock_day_pairs_underflow = eligibility_unlocked_today and (credited_pairs < max(base_pairs - 1, 0))
    normal_day_pairs_capped = (not eligibility_unlocked_today) and (credited_pairs == 5)
    binary_income_given_today = (binary_cash > 0)
    eligibility_bonus_given_today = (eligibility_bonus > 0)
    carry_forward_generated = has_carry_forward
    flashout_triggered_today = has_excess_for_flashout
    washout_triggered_today = has_washout

    # --------------------------------------------
    # Output
    # --------------------------------------------
    return {
        "eligibility_bonus": eligibility_bonus,
        "binary_cash": binary_cash,
        "flash_units": flash_units,
        "repurchase_amount": repurchase_amount,
        "washout_pairs": washout_pairs,
        "cf_left": cf_left,
        "cf_right": cf_right,
        "binary_eligible": binary_eligible,
        "lifetime_pairs": lifetime_pairs,
        "eligibility_unlocked_today": eligibility_unlocked_today,
        # Sponsor fields
        "sponsor_income_target": sponsor_income_target,
        "sponsor_income": sponsor_income,
        # Audit booleans
        "unlocked_today": unlocked_today,
        "can_pay_binary_today": can_pay_binary_today,
        "cap_4_pairs_today": cap_4_pairs_today,
        "cap_5_pairs_today": cap_5_pairs_today,
        "unlock_day_cap_reached": unlock_day_cap_reached,
        "unlock_day_binary_corrected": unlock_day_binary_corrected,
        "has_excess_for_flashout": has_excess_for_flashout,
        "has_washout": has_washout,
        "has_carry_forward": has_carry_forward,
        # Extra audit booleans
        "unlock_pair_income_excluded": unlock_pair_income_excluded,
        "unlock_pair_income_blocked": unlock_pair_income_blocked,
        "unlock_day_pairs_capped": unlock_day_pairs_capped,
        "unlock_day_pairs_underflow": unlock_day_pairs_underflow,
        "normal_day_pairs_capped": normal_day_pairs_capped,
        "binary_income_given_today": binary_income_given_today,
        "eligibility_bonus_given_today": eligibility_bonus_given_today,
        "carry_forward_generated": carry_forward_generated,
        "flashout_triggered_today": flashout_triggered_today,
        "washout_triggered_today": washout_triggered_today,
    }

