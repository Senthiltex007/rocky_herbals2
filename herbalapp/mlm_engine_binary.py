# herbalapp/mlm_engine_binary.py
from django.utils import timezone

# -------------------------------
# Global constants (aligned with daily run engine)
# -------------------------------
PAIR_VALUE = 500                   # direct cash per binary pair
SPONSOR_RATE = 500                 # sponsor mirrors child's binary pairs only
FLASHOUT_UNIT_VALUE = 1000         # per flashout unit to repurchase wallet
DAILY_BINARY_PAIR_LIMIT = 5        # max binary pairs per day
MAX_FLASHOUT_UNITS_PER_DAY = 9     # max flashout units per day


def process_sponsor_income(child, child_binary_cash_for_day, run_date):
    """
    Credits sponsor income for the child's binary cash (fresh daily count),
    with receiver determined by Rule #1 and Rule #2 (root fallback).

    - Rule #1: If child.sponsor == child.placement → income goes to placement.sponsor
    - Rule #2: Else → income goes to direct sponsor
    - Root fallback: If placement.sponsor missing → income goes to direct sponsor
    - Mirrors only child's binary cash (not flashout, not eligibility bonus)
    """
    from herbalapp.models import SponsorIncome

    if not child_binary_cash_for_day or child_binary_cash_for_day <= 0:
        print(f"❌ No sponsor income for {child.member_id} (child_binary_cash_for_day={child_binary_cash_for_day})")
        return

    # Identify receiver per rules
    sponsor_receiver = None
    if child.sponsor:
        if child.sponsor == child.placement:
            if child.placement and child.placement.sponsor:
                sponsor_receiver = child.placement.sponsor
            else:
                sponsor_receiver = child.sponsor  # root fallback
        else:
            sponsor_receiver = child.sponsor

    if not sponsor_receiver:
        print(f"❌ No valid sponsor receiver for {child.member_id}")
        return

    print(f"✅ Creating sponsor income: receiver={sponsor_receiver.member_id}, child={child.member_id}, amount={child_binary_cash_for_day}")
    SponsorIncome.objects.get_or_create(
        sponsor=sponsor_receiver,
        child=child,
        date=run_date,
        defaults={"amount": child_binary_cash_for_day}
    )


def calculate_member_binary_income_for_day(
    left_joins_today: int,
    right_joins_today: int,
    left_cf_before: int,
    right_cf_before: int,
    binary_eligible: bool,
):
    """
    Daily fresh count, aligned with rules:

    - Eligibility occurs by 1:2 or 2:1 (lifetime). On the eligibility day,
      the 1:1 pair inside that pattern is counted as the day's first pair.
      The leftover single member on the heavier side remains available to match later.
    - Binary income: first 5 pairs → ₹500 each (direct cash).
    - Sponsor mirrors only child's binary cash for the day (up to 5 pairs).
    - Flashout: after binary cap, every 5 leftover pairs → 1 unit (₹1000 to repurchase wallet), max 9 units/day.
    - Washout: any pairs beyond binary cap + flashout units (groups of 5) are washed out, not forwarded.
    - Carry forward: only unpaired members remain; pairs are never forwarded.

    Returns a dict with all components for audit and posting.
    """

    # Start with today’s joins + carry forward
    L = int(left_joins_today or 0) + int(left_cf_before or 0)
    R = int(right_joins_today or 0) + int(right_cf_before or 0)

    new_binary_eligible = bool(binary_eligible)
    became_eligible_today = False
    eligibility_income = 0  # child's eligibility bonus (not used for direct cash in final rules)

    # -------------------------------
    # 1) Eligibility check (lifetime)
    # -------------------------------
    if not new_binary_eligible:
        if (L >= 1 and R >= 2) or (L >= 2 and R >= 1):
            new_binary_eligible = True
            became_eligible_today = True

            # Count the 1:1 pair inside the eligibility pattern as today's first pair
            # Deduct 1 from both sides (the leftover single on heavier side stays)
            if L >= 2 and R >= 1 and L > R:
                # 2:1 eligibility (left heavier)
                L -= 1
                R -= 1
            elif R >= 2 and L >= 1 and R >= L:
                # 1:2 eligibility (right heavier or equal)
                L -= 1
                R -= 1
        else:
            # Not yet eligible: any potential pairs today are washed out (no income, not forwarded)
            potential_pairs_today = min(L, R)
            washed_pairs = potential_pairs_today

            # Remove those washed pairs from both sides
            L -= washed_pairs
            R -= washed_pairs

            left_cf_after = L
            right_cf_after = R

            total_income = 0
            child_total_for_sponsor = 0  # sponsor only mirrors binary cash

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
                "left_cf_after": left_cf_after,
                "right_cf_after": right_cf_after,
                "total_income": total_income,
                "child_total_for_sponsor": child_total_for_sponsor,
            }

    # -------------------------------
    # 2) After eligibility: only 1:1 pairs count
    # -------------------------------
    total_pairs_available = min(L, R)

    # -------------------------------
    # 3) Binary layer (first 5 pairs)
    # -------------------------------
    binary_pairs = min(total_pairs_available, DAILY_BINARY_PAIR_LIMIT)
    binary_income = binary_pairs * PAIR_VALUE

    # Consume pairs used for binary
    L -= binary_pairs
    R -= binary_pairs

    # -------------------------------
    # 4) Flashout layer (groups of 5, max 9 units/day)
    # -------------------------------
    pairs_remaining_after_binary = min(L, R)
    flashout_units = min(pairs_remaining_after_binary // 5, MAX_FLASHOUT_UNITS_PER_DAY)
    flashout_pairs_used = flashout_units * 5
    repurchase_wallet_bonus = flashout_units * FLASHOUT_UNIT_VALUE

    # Consume pairs used for flashout
    L -= flashout_pairs_used
    R -= flashout_pairs_used

    # -------------------------------
    # 5) Washout (beyond binary + flashout caps)
    # -------------------------------
    washed_pairs = min(L, R)

    # Consume washed pairs (not forwarded)
    L -= washed_pairs
    R -= washed_pairs

    # -------------------------------
    # 6) Carry forward (only unpaired members remain)
    # -------------------------------
    left_cf_after = L
    right_cf_after = R

    # -------------------------------
    # 7) Totals
    # -------------------------------
    total_income = binary_income  # direct income; eligibility_income is not used as cash in final rules
    child_total_for_sponsor = binary_income  # sponsor mirrors only child's binary cash (max 5 pairs)

    return {
        "new_binary_eligible": new_binary_eligible,
        "became_eligible_today": became_eligible_today,
        "eligibility_income": eligibility_income,
        "binary_pairs": binary_pairs,
        "binary_income": binary_income,
        "flashout_units": flashout_units,
        "flashout_pairs_used": flashout_pairs_used,
        "repurchase_wallet_bonus": repurchase_wallet_bonus,
        "washed_pairs": washed_pairs,
        "left_cf_after": left_cf_after,
        "right_cf_after": right_cf_after,
        "total_income": total_income,
        "child_total_for_sponsor": child_total_for_sponsor,
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

