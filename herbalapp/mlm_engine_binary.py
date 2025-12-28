# herbalapp/mlm_engine_binary.py
# ----------------------------------------------------------
# FINAL MASTER MLM ENGINE (Binary + Sponsor + Flashout + Washout)
# ----------------------------------------------------------

# ---------------------------------------
# Global constants
# ---------------------------------------
PAIR_VALUE = 500
FLASHOUT_UNIT_VALUE = 1000
DAILY_BINARY_PAIR_LIMIT = 5         # daily binary pairs cap
MAX_FLASHOUT_UNITS_PER_DAY = 9      # each unit = 5 pairs to repurchase wallet
ELIGIBILITY_BONUS = 500

from django.utils import timezone
import datetime
from herbalapp.models import IncomeRecord, SponsorIncome, Member

def distribute_income(child, eligibility_income, binary_income):
    """
    Boolean-oriented sponsor/parent/grandparent income distribution.
    Applied to ALL members universally.
    """

    total_for_sponsor = eligibility_income + binary_income

    # --- Parent Income Check ---
    if child.parent and child.parent.binary_eligible:
        child.parent.sponsor_income += total_for_sponsor
        print(f"Parent {child.parent.auto_id} credited ₹{total_for_sponsor}")

        # --- Grandparent Income Check ---
        if child.parent.parent and child.parent.parent.binary_eligible:
            child.parent.parent.sponsor_income += total_for_sponsor
            print(f"Grandparent {child.parent.parent.auto_id} credited ₹{total_for_sponsor}")

    # --- Sponsor Income Check (if sponsor ≠ parent) ---
    if child.sponsor and child.sponsor != child.parent:
        if child.sponsor.binary_eligible:
            child.sponsor.sponsor_income += total_for_sponsor
            print(f"Sponsor {child.sponsor.auto_id} credited ₹{total_for_sponsor}")

def process_sponsor_income(child, child_total_for_sponsor, run_date, child_became_eligible_today=False):
    """
    Universal sponsor income processor:
    - Always check parent (placement) income
    - Always check grandparent (placement of placement) income
    - If sponsor ≠ parent, check sponsor income
    - Fallback: use sponsor_id if relation missing
    """

    sponsor_amount = int(child_total_for_sponsor or 0)
    if sponsor_amount <= 0:
        return

    # --- Parent Income Check (placement) ---
    if child.placement and child.placement.binary_eligible:
        SponsorIncome.objects.create(
            sponsor=child.placement,
            child=child,
            amount=sponsor_amount,
            date=run_date,
            eligibility_bonus=child_became_eligible_today
        )
        print(f"Parent {child.placement.auto_id} credited ₹{sponsor_amount}")

        # --- Grandparent Income Check (placement of placement) ---
        if child.placement.placement and child.placement.placement.binary_eligible:
            SponsorIncome.objects.create(
                sponsor=child.placement.placement,
                child=child,
                amount=sponsor_amount,
                date=run_date,
                eligibility_bonus=child_became_eligible_today
            )
            print(f"Grandparent {child.placement.placement.auto_id} credited ₹{sponsor_amount}")

    # --- Sponsor Income Check (if sponsor ≠ parent) ---
    sponsor_receiver = None
    if child.sponsor and child.sponsor != child.placement:
        sponsor_receiver = child.sponsor
    elif getattr(child, "sponsor_id", None):
        sponsor_receiver = Member.objects.filter(id=child.sponsor_id).first()

    if sponsor_receiver and sponsor_receiver.binary_eligible:
        SponsorIncome.objects.create(
            sponsor=sponsor_receiver,
            child=child,
            amount=sponsor_amount,
            date=run_date,
            eligibility_bonus=child_became_eligible_today
        )
        print(f"Sponsor {sponsor_receiver.auto_id} credited ₹{sponsor_amount}")

# ---------------------------------------
# Binary income calculator (final boolean fix + constants)
# ---------------------------------------
def calculate_member_binary_income_for_day(
    left_joins_today,
    right_joins_today,
    left_cf_before,
    right_cf_before,
    binary_eligible,
    member,
    run_date
):
    # Normalize counts
    L = int(left_joins_today or 0) + int(left_cf_before or 0)
    R = int(right_joins_today or 0) + int(right_cf_before or 0)

    new_binary_eligible = bool(binary_eligible)
    became_eligible_today = False
    eligibility_income = 0

    # 1) Eligibility check
    if not new_binary_eligible:
        cond_12 = (L >= 1 and R >= 2)
        cond_21 = (L >= 2 and R >= 1)
        if cond_12 or cond_21:
            new_binary_eligible = True
            became_eligible_today = True
            eligibility_income = ELIGIBILITY_BONUS
            # Strict unlock lock: consume the unlocking asymmetry fully
            if cond_12:
                # 1:2 → consume 1 from L and 2 from R
                L -= 1
                R -= 2
            else:
                # 2:1 → consume 2 from L and 1 from R
                L -= 2
                R -= 1
            L = max(L, 0)
            R = max(R, 0)
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
                "repurchase_wallet_bonus": 0,
                "washed_pairs": washed_pairs,
                "left_cf_after": L,
                "right_cf_after": R,
                "total_income": 0,
                "child_total_for_sponsor": 0,
                "unlock_day_cap_reached": False,
                "flashout_triggered_today": False,
                "washout_triggered_today": True if washed_pairs > 0 else False,
                "carry_forward_generated": (L > 0 or R > 0),

                # --- NEW: member join details ---
                "member_not_yet_joined": False,   # here eligibility failed but member exists
                "joined_member_auto_id": member.auto_id,
                "joined_member_sponsor": getattr(member.sponsor, "auto_id", None),
                "joined_member_placement": getattr(member.placement, "auto_id", None),
                "joined_date": getattr(member, "joined_date", None),
            }

    # 2) Binary income — fresh 1:1 only, daily cap 5
    total_pairs_available = min(L, R)
    already_counted_first_pair = 1 if became_eligible_today else 0
    remaining_cap = max(DAILY_BINARY_PAIR_LIMIT - already_counted_first_pair, 0)

    binary_pairs_today = min(total_pairs_available, remaining_cap)
    total_binary_pairs_for_day = binary_pairs_today + already_counted_first_pair
    binary_income = total_binary_pairs_for_day * PAIR_VALUE

    # Consume only fresh pairs
    L -= binary_pairs_today
    R -= binary_pairs_today

    # 3) Flashout — 5 pairs/unit → ₹1000, max 9 units/day
    pairs_remaining_after_binary = min(L, R)
    flashout_units = min(pairs_remaining_after_binary // DAILY_BINARY_PAIR_LIMIT, MAX_FLASHOUT_UNITS_PER_DAY)
    flashout_pairs_used = flashout_units * DAILY_BINARY_PAIR_LIMIT
    repurchase_wallet_bonus = flashout_units * FLASHOUT_UNIT_VALUE

    L -= flashout_pairs_used
    R -= flashout_pairs_used
    # --- Spot update of repurchase wallet ---
    if repurchase_wallet_bonus > 0:
        member.repurchase_wallet_balance += repurchase_wallet_bonus
        member.save(update_fields=["repurchase_wallet_balance"])
        print(f"{member.auto_id} repurchase wallet updated ₹{repurchase_wallet_bonus} (spot)")

    # 4) Washout — any remaining pairs beyond flashout
    washed_pairs = min(L, R)
    L -= washed_pairs
    R -= washed_pairs

    # 5) Carry forward — single side remains
    left_cf_after = L
    right_cf_after = R

    # 6) Totals
    child_total_for_sponsor = eligibility_income + binary_income   # mirror = eligibility + binary (as required)
    total_income = eligibility_income + binary_income + repurchase_wallet_bonus

    # ✅ Exact day key (IST aware timestamp)
    run_datetime = timezone.now()

    # 7) Persist — always create/update record even if total_income = 0
    existing_record = IncomeRecord.objects.filter(
        member=member,
        type="binary_engine",
        created_at__date=run_date
    ).first()

    if existing_record:
        # Update all relevant fields
        existing_record.amount = total_income
        existing_record.sponsor_income = child_total_for_sponsor
        existing_record.binary_income = binary_income
        existing_record.wallet_income = repurchase_wallet_bonus
        existing_record.washed_pairs = washed_pairs
        existing_record.left_cf_after = left_cf_after
        existing_record.right_cf_after = right_cf_after
        existing_record.save(update_fields=[
            "amount","sponsor_income","binary_income","wallet_income",
            "washed_pairs","left_cf_after","right_cf_after"
        ])
        record_created = False
    else:
        IncomeRecord.objects.create(
            member=member,
            type="binary_engine",
            amount=total_income,
            created_at=run_datetime,
            sponsor_income=child_total_for_sponsor,
            eligibility_income=eligibility_income,
            binary_income=binary_income,
            wallet_income=repurchase_wallet_bonus,
            washed_pairs=washed_pairs,
            left_cf_after=left_cf_after,
            right_cf_after=right_cf_after,
            total_income=total_income
        )
        record_created = True

    # 8) Update member (non-financial quick fields)
    member.flashout_units = flashout_units
    member.sponsor_income = child_total_for_sponsor
    member.washed_pairs = washed_pairs
    member.save(update_fields=[
        "flashout_units",
        "sponsor_income",
        "washed_pairs"
    ])

    # 9) Sponsor income mirror (routing by 3 rules)
    process_sponsor_income(
        member,
        child_total_for_sponsor,
        run_date,
        became_eligible_today
    )

    # 10) Audit return
    return {
        "new_binary_eligible": new_binary_eligible,
        "became_eligible_today": became_eligible_today,
        "eligibility_income": eligibility_income,
        "binary_pairs": total_binary_pairs_for_day,
        "binary_income": binary_income,
        "flashout_units": flashout_units,
        "repurchase_wallet_bonus": repurchase_wallet_bonus,
        "washed_pairs": washed_pairs,
        "left_cf_after": left_cf_after,
        "right_cf_after": right_cf_after,
        "total_income": total_income,
        "child_total_for_sponsor": child_total_for_sponsor,
        "unlock_day_cap_reached": (total_binary_pairs_for_day == DAILY_BINARY_PAIR_LIMIT),
        "flashout_triggered_today": (flashout_units > 0),
        "washout_triggered_today": (washed_pairs > 0),
        "carry_forward_generated": (left_cf_after > 0 or right_cf_after > 0),
        "record_created": record_created
    }

