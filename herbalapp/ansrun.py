# herbalapp/ansrun.py
from django.utils import timezone
from herbalapp.models import SponsorIncome

# Constants
PAIR_VALUE = 500
FLASHOUT_UNIT_VALUE = 1000
DAILY_BINARY_PAIR_LIMIT = 5
MAX_FLASHOUT_UNITS_PER_DAY = 9
ELIGIBILITY_BONUS = 500

def process_sponsor_income(child, child_binary_cash_for_day, run_date, child_became_eligible_today=False):
    base_cash = int(child_binary_cash_for_day or 0)
    eligibility_bonus = ELIGIBILITY_BONUS if child_became_eligible_today else 0
    sponsor_amount = base_cash + eligibility_bonus
    if sponsor_amount <= 0:
        return 0

    # Routing rules
    sponsor_receiver = None
    if child.sponsor:
        if child.placement and (child.sponsor == child.placement):
            sponsor_receiver = (child.placement.sponsor or child.sponsor)
        else:
            sponsor_receiver = child.sponsor

    if not sponsor_receiver:
        return 0

    # Eligibility gate
    receiver_is_eligible = False
    if hasattr(sponsor_receiver, "binary_eligible"):
        receiver_is_eligible = bool(getattr(sponsor_receiver, "binary_eligible"))
    elif hasattr(sponsor_receiver, "lifetime_pairs"):
        receiver_is_eligible = (int(getattr(sponsor_receiver, "lifetime_pairs") or 0) >= 1)

    if not receiver_is_eligible:
        return 0

    obj, created = SponsorIncome.objects.get_or_create(
        sponsor=sponsor_receiver,
        child=child,
        date=run_date,
        defaults={"amount": sponsor_amount}
    )
    if not created and obj.amount != sponsor_amount:
        obj.amount = sponsor_amount
        obj.save(update_fields=["amount"])
    return sponsor_amount

def calculate_member_binary_income_for_day(left_joins_today, right_joins_today, left_cf_before, right_cf_before, binary_eligible):
    L = int(left_joins_today or 0) + int(left_cf_before or 0)
    R = int(right_joins_today or 0) + int(right_cf_before or 0)

    new_binary_eligible = bool(binary_eligible)
    became_eligible_today = False
    eligibility_income = 0

    if not new_binary_eligible:
        if (L >= 1 and R >= 2) or (L >= 2 and R >= 1):
            new_binary_eligible = True
            became_eligible_today = True
            eligibility_income = ELIGIBILITY_BONUS
            L -= 1
            R -= 1
        else:
            washed_pairs = min(L, R)
            L -= washed_pairs
            R -= washed_pairs
            return {
                "new_binary_eligible": new_binary_eligible,
                "became_eligible_today": False,
                "eligibility_income": 0,
                "binary_pairs": 0,
                "binary_income": 0,
                "flashout_units": 0,
                "flashout_pairs_used": 0,
                "repurchase_wallet_bonus": 0,
                "washed_pairs": washed_pairs,
                "left_cf_after": L,
                "right_cf_after": R,
                "total_income": 0,
                "child_cash_for_day": 0,
                "child_total_for_sponsor": 0,
                # Audit flags
                "check_binary_eligible": False,
                "check_sponsor_gate": False,
                "check_cf": (L > 0 or R > 0),
                "check_over_binary_cap": False,
                "check_over_flashout_cap": False,
            }

    total_pairs_available = min(L, R)
    already_counted_first_pair = 1 if became_eligible_today else 0
    remaining_cap = max(DAILY_BINARY_PAIR_LIMIT - already_counted_first_pair, 0)

    binary_pairs_today = min(total_pairs_available, remaining_cap)
    total_binary_pairs_for_day = binary_pairs_today + already_counted_first_pair
    binary_income = total_binary_pairs_for_day * PAIR_VALUE

    L -= binary_pairs_today
    R -= binary_pairs_today

    pairs_remaining_after_binary = min(L, R)
    flashout_units = min(pairs_remaining_after_binary // 5, MAX_FLASHOUT_UNITS_PER_DAY)
    flashout_pairs_used = flashout_units * 5
    repurchase_wallet_bonus = flashout_units * FLASHOUT_UNIT_VALUE

    L -= flashout_pairs_used
    R -= flashout_pairs_used

    washed_pairs = min(L, R)
    L -= washed_pairs
    R -= washed_pairs

    left_cf_after = L
    right_cf_after = R

    child_cash_for_day = binary_income
    total_income = child_cash_for_day
    child_total_for_sponsor = (eligibility_income or 0) + (binary_income or 0)

    return {
        "new_binary_eligible": new_binary_eligible,
        "became_eligible_today": became_eligible_today,
        "eligibility_income": eligibility_income,
        "binary_pairs": total_binary_pairs_for_day,
        "binary_income": binary_income,
        "flashout_units": flashout_units,
        "flashout_pairs_used": flashout_pairs_used,
        "repurchase_wallet_bonus": repurchase_wallet_bonus,
        "washed_pairs": washed_pairs,
        "left_cf_after": left_cf_after,
        "right_cf_after": right_cf_after,
        "total_income": total_income,
        "child_cash_for_day": child_cash_for_day,
        "child_total_for_sponsor": child_total_for_sponsor,
        # Audit flags
        "check_binary_eligible": new_binary_eligible,
        "check_sponsor_gate": None,
        "check_cf": (left_cf_after > 0 or right_cf_after > 0),
        "check_over_binary_cap": (total_binary_pairs_for_day > DAILY_BINARY_PAIR_LIMIT),
        "check_over_flashout_cap": (flashout_units > MAX_FLASHOUT_UNITS_PER_DAY),
    }

