# herbalapp/mlm_engine_binary.py
# ----------------------------------------------------------
# FINAL MASTER MLM ENGINE (Binary + Sponsor + Flashout + Washout)
# ----------------------------------------------------------

# ---------------------------------------
# Global constants
# ---------------------------------------
PAIR_VALUE = 500
FLASHOUT_UNIT_VALUE = 1000
DAILY_BINARY_PAIR_LIMIT = 5
MAX_FLASHOUT_UNITS_PER_DAY = 9
ELIGIBILITY_BONUS = 500

from django.utils import timezone
from herbalapp.models import IncomeRecord, SponsorIncome, Member

# ---------------------------------------
# Sponsor income processor
# ---------------------------------------
def process_sponsor_income(child, child_total_for_sponsor, run_date, child_became_eligible_today=False):
    sponsor_amount = int(child_total_for_sponsor or 0)
    if sponsor_amount <= 0:
        return

    # --- Parent Income Check ---
    if child.placement and child.placement.binary_eligible:
        SponsorIncome.objects.create(
            sponsor=child.placement,
            child=child,
            amount=sponsor_amount,
            date=run_date
        )
        print(f"Parent {child.placement.member_id} credited ₹{sponsor_amount}")

        # --- Grandparent Income Check ---
        if child.placement.placement and child.placement.placement.binary_eligible:
            SponsorIncome.objects.create(
                sponsor=child.placement.placement,
                child=child,
                amount=sponsor_amount,
                date=run_date
            )
            print(f"Grandparent {child.placement.placement.member_id} credited ₹{sponsor_amount}")

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
            date=run_date
        )
        print(f"Sponsor {sponsor_receiver.member_id} credited ₹{sponsor_amount}")

# ---------------------------------------
# Binary income calculator
# ---------------------------------------
def calculate_member_binary_income_for_day(
    *,
    left_joins_today=0,
    right_joins_today=0,
    left_cf_before=0,
    right_cf_before=0,
    binary_eligible=None,
    member=None,
    run_date=None
):
    L = int(left_joins_today or 0) + int(left_cf_before or 0)
    R = int(right_joins_today or 0) + int(right_cf_before or 0)

    new_binary_eligible = bool(binary_eligible)
    became_eligible_today = False
    eligibility_income = 0

    # Eligibility unlock
    if not new_binary_eligible:
        cond_12 = (L >= 1 and R >= 2)
        cond_21 = (L >= 2 and R >= 1)
        if cond_12 or cond_21:
            new_binary_eligible = True
            became_eligible_today = True
            eligibility_income = ELIGIBILITY_BONUS
            if cond_12:
                L -= 1; R -= 2
            else:
                L -= 2; R -= 1
            L = max(L, 0); R = max(R, 0)
        else:
            washed_pairs = min(L, R)
            L -= washed_pairs; R -= washed_pairs
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
                "washout_triggered_today": washed_pairs > 0,
                "carry_forward_generated": (L > 0 or R > 0),
                "joined_member_member_id": member.member_id,
                "joined_member_sponsor": getattr(member.sponsor, "member_id", None),
                "joined_member_placement": getattr(member.placement, "member_id", None),
                "joined_date": getattr(member, "joined_date", None),
            }

    # Binary income
    total_pairs_available = min(L, R)
    already_counted_first_pair = 1 if became_eligible_today else 0
    remaining_cap = max(DAILY_BINARY_PAIR_LIMIT - already_counted_first_pair, 0)
    binary_pairs_today = min(total_pairs_available, remaining_cap)
    total_binary_pairs_for_day = binary_pairs_today + already_counted_first_pair
    binary_income = total_binary_pairs_for_day * PAIR_VALUE
    L -= binary_pairs_today; R -= binary_pairs_today

    # Flashout
    pairs_remaining_after_binary = min(L, R)
    flashout_units = min(pairs_remaining_after_binary // DAILY_BINARY_PAIR_LIMIT, MAX_FLASHOUT_UNITS_PER_DAY)
    flashout_pairs_used = flashout_units * DAILY_BINARY_PAIR_LIMIT
    repurchase_wallet_bonus = flashout_units * FLASHOUT_UNIT_VALUE
    L -= flashout_pairs_used; R -= flashout_pairs_used

    if repurchase_wallet_bonus > 0:
        member.repurchase_wallet_balance += repurchase_wallet_bonus
        member.save(update_fields=["repurchase_wallet_balance"])
        print(f"{member.member_id} repurchase wallet updated ₹{repurchase_wallet_bonus}")

    # Washout
    washed_pairs = min(L, R)
    L -= washed_pairs; R -= washed_pairs

    left_cf_after = L; right_cf_after = R
    child_total_for_sponsor = eligibility_income + binary_income
    total_income = eligibility_income + binary_income + repurchase_wallet_bonus
    run_datetime = timezone.now()

    # Persist IncomeRecord
    existing_record = IncomeRecord.objects.filter(
        member=member, type="binary_engine", created_at__date=run_date
    ).first()
    if existing_record:
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

    # Sponsor income mirror
    process_sponsor_income(member, child_total_for_sponsor, run_date, became_eligible_today)

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

