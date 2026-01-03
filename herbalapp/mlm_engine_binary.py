# herbalapp/mlm_engine_binary.py

from decimal import Decimal

PAIR_VALUE = Decimal("500.00")
DAILY_BINARY_PAIR_LIMIT = 5
FLASHOUT_UNIT_VALUE = Decimal("1000.00")
MAX_FLASHOUT_UNITS_PER_DAY = 9


def calculate_member_binary_income_for_day(
    *,
    left_joins_today=0,
    right_joins_today=0,
    left_cf_before=0,
    right_cf_before=0,
    binary_eligible=False,
    eligibility_today=False,   # 🔥 from signals.py
    member=None,
    run_date=None
):
    # ----------------------------
    # Total available legs
    # ----------------------------
    L = int(left_joins_today or 0) + int(left_cf_before or 0)
    R = int(right_joins_today or 0) + int(right_cf_before or 0)

    # ----------------------------
    # Locked first pair (2:1 or 1:2) already handled in signals
    # Just ignore binary income if eligibility_today
    # ----------------------------
    total_pairs = min(L, R)

    if eligibility_today:
        binary_pairs_today = 0   # ❌ NO binary income today
    else:
        binary_pairs_today = min(total_pairs, DAILY_BINARY_PAIR_LIMIT)

    binary_income = Decimal(binary_pairs_today) * PAIR_VALUE
    L -= binary_pairs_today
    R -= binary_pairs_today

    # ----------------------------
    # Flashout
    # ----------------------------
    pairs_after_binary = min(L, R)
    flashout_units = min(
        pairs_after_binary // DAILY_BINARY_PAIR_LIMIT,
        MAX_FLASHOUT_UNITS_PER_DAY
    )

    flashout_pairs_used = flashout_units * DAILY_BINARY_PAIR_LIMIT
    repurchase_wallet_bonus = Decimal(flashout_units) * FLASHOUT_UNIT_VALUE

    L -= flashout_pairs_used
    R -= flashout_pairs_used

    # ----------------------------
    # Washout
    # ----------------------------
    washed_pairs = min(L, R)
    L -= washed_pairs
    R -= washed_pairs

    # ----------------------------
    # Return full audit dictionary
    # ----------------------------
    return {
        # Core incomes
        "binary_pairs": int(binary_pairs_today),
        "binary_income": binary_income,
        "flashout_units": int(flashout_units),
        "repurchase_wallet_bonus": repurchase_wallet_bonus,
        "washed_pairs": int(washed_pairs),

        # Carry forward
        "left_cf_after": int(L),
        "right_cf_after": int(R),

        # Audit flags
        "eligibility_day_locked": eligibility_today,
        "pairs_after_binary": int(pairs_after_binary),
        "unlock_day_cap_reached": (binary_pairs_today == DAILY_BINARY_PAIR_LIMIT),
        "flashout_triggered_today": (flashout_units > 0),
        "washout_triggered_today": (washed_pairs > 0),
        "carry_forward_generated": (L > 0 or R > 0),
    }

