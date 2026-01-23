# ==========================================================
# herbalapp/mlm/core_pair_engine.py
# ==========================================================

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport

ROOT_ID = "rocky001"
PAIR_VALUE = Decimal("500")
ELIGIBILITY_BONUS = Decimal("500")
DAILY_BINARY_PAIR_LIMIT = 5
FLASHOUT_GROUP_SIZE = 5
FLASHOUT_VALUE = 1000
MAX_DAILY_FLASHOUTS = 9

# ----------------------------------------------------------
# 1️⃣ BINARY & ELIGIBILITY CALCULATION
# ----------------------------------------------------------
def calculate_binary(member, left_today, right_today, left_cf, right_cf):
    L = left_today + left_cf
    R = right_today + right_cf

    new_binary_eligible = member.binary_eligible
    eligibility_income = 0
    binary_pairs_paid = 0
    binary_income = 0
    flashout_units = 0
    flashout_pairs_used = 0
    flashout_income = 0
    washed_pairs = 0

    # -------------------------------
    # Binary Eligibility Check
    # -------------------------------
    if not member.binary_eligible:
        if (L >= 2 and R >= 1) or (L >= 1 and R >= 2):
            new_binary_eligible = True
            result["eligibility_income"] = ELIGIBILITY_BONUS

            # Deduct eligibility pair
            if L >= 2 and R >= 1:
                L -= 2
                R -= 1
            else:
                L -= 1
                R -= 2

            total_pairs_available = min(L, R)
            binary_pairs_paid = min(total_pairs_available, 4)
            binary_income = paid_pairs * PAIR_VALUE
            L -= binary_pairs_paid
            R -= binary_pairs_paid

            pairs_remaining_after_binary = total_pairs_available - binary_pairs_paid
            flashout_units = min(pairs_remaining_after_binary // FLASHOUT_GROUP_SIZE, MAX_DAILY_FLASHOUTS)
            flashout_pairs_used = flashout_units * FLASHOUT_GROUP_SIZE
            flashout_income = flashout_units * FLASHOUT_VALUE
            L -= flashout_pairs_used
            R -= flashout_pairs_used

            washed_pairs = pairs_remaining_after_binary - flashout_pairs_used
            total_income = result["eligibility_income"] + binary_income + flashout_income

            return {
                "new_binary_eligible": new_binary_eligible,
                "eligibility_income": result["eligibility_income"],
                "binary_pairs_paid": binary_pairs_paid,
                "binary_income": binary_income,
                "flashout_units": flashout_units,
                "flashout_pairs_used": flashout_pairs_used,
                "flashout_income": flashout_income,
                "washed_pairs": washed_pairs,
                "left_cf_after": L,
                "right_cf_after": R,
                "total_income": total_income,
            }

    # -------------------------------
    # After eligibility → daily 1:1 binary max 5
    # -------------------------------
    total_pairs_available = min(L, R)
    binary_pairs_paid = min(total_pairs_available, DAILY_BINARY_PAIR_LIMIT)
    binary_income = paid_pairs * PAIR_VALUE
    L -= binary_pairs_paid
    R -= binary_pairs_paid

    pairs_remaining_after_binary = total_pairs_available - binary_pairs_paid
    flashout_units = min(pairs_remaining_after_binary // FLASHOUT_GROUP_SIZE, MAX_DAILY_FLASHOUTS)
    flashout_pairs_used = flashout_units * FLASHOUT_GROUP_SIZE
    flashout_income = flashout_units * FLASHOUT_VALUE
    L -= flashout_pairs_used
    R -= flashout_pairs_used

    washed_pairs = pairs_remaining_after_binary - flashout_pairs_used
    left_cf_after = L
    right_cf_after = R
    total_income = result["eligibility_income"] + binary_income + flashout_income

    return {
        "new_binary_eligible": new_binary_eligible,
        "eligibility_income": result["eligibility_income"],
        "binary_pairs_paid": binary_pairs_paid,
        "binary_income": binary_income,
        "flashout_units": flashout_units,
        "flashout_pairs_used": flashout_pairs_used,
        "flashout_income": flashout_income,
        "washed_pairs": washed_pairs,
        "left_cf_after": left_cf_after,
        "right_cf_after": right_cf_after,
        "total_income": total_income,
    }

# ----------------------------------------------------------
# 3️⃣ FULL DAILY ENGINE
# ----------------------------------------------------------
@transaction.atomic
def run_daily_engine(run_date=None):
    if not run_date:
        run_date = timezone.now().date()

    # ✅ Exclude ROOT_ID
    members = Member.objects.filter(is_active=True).exclude(auto_id=ROOT_ID).order_by("id")

    # -------------------------------
    # Step 1: Binary + Eligibility
    # -------------------------------
    for member in members:
        report, _ = DailyIncomeReport.objects.get_or_create(member=member, date=run_date)

        # -------------------------------
        # TODAY joins (DATE BASED ONLY)
        # ❌ Do not use left_child()/right_child()
        # -------------------------------
        left_today = 0
        right_today = 0

        res = calculate_binary(member, left_today, right_today, report.left_cf, report.right_cf)

        report.binary_income = res["binary_income"]
        report.binary_eligibility_income = res["eligibility_income"]
        report.flashout_units = res["flashout_units"]
        report.flashout_wallet_income = res["flashout_income"]  # ✅ store flashout wallet income
        report.left_cf = res["left_cf_after"]
        report.right_cf = res["right_cf_after"]
        report.total_income = res["binary_income"] + res["eligibility_income"] + res["flashout_income"]
        report.save()

        if res["new_binary_eligible"] and not member.binary_eligible:
            member.binary_eligible = True
            member.save(update_fields=["binary_eligible"])

    # -------------------------------
    # Step 3: Final Total
    # -------------------------------
    for report in DailyIncomeReport.objects.filter(date=run_date):
        report.total_income = (
            (report.binary_income or 0) +
            (report.binary_eligibility_income or 0) +
            (report.sponsor_income or 0) +
            (report.flashout_wallet_income or 0)  # ✅ added flashout in total
        )
        report.save(update_fields=["total_income"])

