# test_binary_engine.py

def calculate_member_binary_income_for_day(
    left_cf_before,
    right_cf_before,
    left_joins_today,
    right_joins_today,
    binary_eligible
):
    eligibility_income = 0
    binary_income = 0
    flashout_units = 0

    # --- Eligibility unlock check ---
    if not binary_eligible:
        total_left = left_cf_before + left_joins_today
        total_right = right_cf_before + right_joins_today
        if (total_left >= 2 and total_right >= 1) or (total_left >= 1 and total_right >= 2):
            eligibility_income = 500
            binary_eligible = True   # lifetime flag

    # --- Binary income check ---
    if binary_eligible:
        pairs_today = min(left_joins_today, right_joins_today)
        if pairs_today > 5:
            binary_income = 5 * 500
            flashout_units = pairs_today - 5
        else:
            binary_income = pairs_today * 500

    return {
        "eligibility_income": eligibility_income,
        "binary_income": binary_income,
        "flashout_units": flashout_units,
        "binary_eligible": binary_eligible,
        "left_cf_after": left_cf_before + left_joins_today,
        "right_cf_after": right_cf_before + right_joins_today,
        "washed_pairs": 0,
        "repurchase_wallet_bonus": 0,
        "total_income": eligibility_income + binary_income,
    }


# --- Run test ---
if __name__ == "__main__":
    result = calculate_member_binary_income_for_day(
        left_cf_before=0,
        right_cf_before=0,
        left_joins_today=2,
        right_joins_today=1,
        binary_eligible=False
    )
    print(result)

