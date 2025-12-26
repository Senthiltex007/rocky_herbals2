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

# ---------------------------------------
# Sponsor income processor (with sponsor_id fallback)
# ---------------------------------------
def process_sponsor_income(child, child_total_for_sponsor, run_date, child_became_eligible_today=False):
    """
    Amount mirrored = (child eligibility bonus if unlocked today) + (child binary cash for day).
    Routing:
    - If placement == sponsor → receiver = placement.sponsor (fallback to child.sponsor)
    - Else → receiver = child.sponsor
    - Fallback: use sponsor_id if relation is missing.
    Gate: receiver must be binary eligible (≥1 lifetime pair or binary_eligible True).
    """
    sponsor_amount = int(child_total_for_sponsor or 0)
    if sponsor_amount <= 0:
        return

    sponsor_receiver = None
    if getattr(child, "sponsor", None):
        if child.placement and (child.sponsor == child.placement):
            sponsor_receiver = (child.placement.sponsor or child.sponsor)
        else:
            sponsor_receiver = child.sponsor
    elif getattr(child, "sponsor_id", None):
        sponsor_receiver = Member.objects.filter(id=child.sponsor_id).first()

    if not sponsor_receiver:
        return

    receiver_is_eligible = False
    if hasattr(sponsor_receiver, "binary_eligible"):
        receiver_is_eligible = bool(sponsor_receiver.binary_eligible)
    elif hasattr(sponsor_receiver, "lifetime_pairs"):
        receiver_is_eligible = (int(sponsor_receiver.lifetime_pairs or 0) >= 1)

    if not receiver_is_eligible:
        return

    SponsorIncome.objects.get_or_create(
        sponsor=sponsor_receiver,
        child=child,
        date=run_date,
        defaults={"amount": sponsor_amount}
    )

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
            }

    # 2) Binary income
    total_pairs_available = min(L, R)
    already_counted_first_pair = 1 if became_eligible_today else 0
    remaining_cap = max(DAILY_BINARY_PAIR_LIMIT - already_counted_first_pair, 0)

    binary_pairs_today = min(total_pairs_available, remaining_cap)
    total_binary_pairs_for_day = binary_pairs_today + already_counted_first_pair
    binary_income = total_binary_pairs_for_day * PAIR_VALUE

    L -= binary_pairs_today
    R -= binary_pairs_today

    # 3) Flashout
    pairs_remaining_after_binary = min(L, R)
    flashout_units = min(pairs_remaining_after_binary // DAILY_BINARY_PAIR_LIMIT, MAX_FLASHOUT_UNITS_PER_DAY)
    flashout_pairs_used = flashout_units * DAILY_BINARY_PAIR_LIMIT
    repurchase_wallet_bonus = flashout_units * FLASHOUT_UNIT_VALUE

    L -= flashout_pairs_used
    R -= flashout_pairs_used

    # 4) Washout
    washed_pairs = min(L, R)
    L -= washed_pairs
    R -= washed_pairs

    # 5) Carry forward
    left_cf_after = L
    right_cf_after = R

    # 6) Totals
    child_total_for_sponsor = eligibility_income + binary_income
    total_income = eligibility_income + binary_income + repurchase_wallet_bonus

    # Exact day key
    run_datetime = timezone.make_aware(
        datetime.datetime.combine(run_date, datetime.time.min)
    )

    # 7) Persist — boolean‑rich duplicate prevention (single authoritative block)
    existing_record = IncomeRecord.objects.filter(
        member=member,
        type="binary_engine",
        created_at=run_datetime
    ).first()

    if existing_record:
        if existing_record.amount != total_income:
            existing_record.amount = total_income
            existing_record.save(update_fields=["amount"])
        record_created = False
    else:
        record_to_update = IncomeRecord.objects.filter(
            member=member,
            type="binary_engine",
            created_at__date=run_date
        ).first()

        if record_to_update:
            if record_to_update.amount != total_income:
                record_to_update.amount = total_income
                record_to_update.save(update_fields=["amount"])
            record_created = False
        else:
            IncomeRecord.objects.create(
                member=member,
                type="binary_engine",
                amount=total_income,
                created_at=run_datetime
            )
            record_created = True

    # 8) Sponsor income mirror
    process_sponsor_income(member, child_total_for_sponsor, run_date, became_eligible_today)

    # 9) Audit return
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

