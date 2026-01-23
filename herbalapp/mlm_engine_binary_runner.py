# ==========================================================
# herbalapp/mlm_engine_binary_runner.py
# FINAL STABLE VERSION (Corrected Eligibility Day Logic)
# ==========================================================
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport

PAIR_VALUE = Decimal("500")
ELIGIBILITY_BONUS = Decimal("500")
DAILY_BINARY_PAIR_LIMIT = 5
FLASHOUT_GROUP_SIZE = 5
FLASHOUT_VALUE = Decimal("1000")
MAX_DAILY_FLASHOUTS = 9


# ----------------------------------------------------------
# Helper : count descendants (FIXED – model safe)
# ----------------------------------------------------------
def count_all_descendants(member, side):
    """
    side = 'left' or 'right'
    """
    if not member:
        return 0

    children = Member.objects.filter(parent=member, side=side)
    total = children.count()

    for child in children:
        total += count_all_descendants(child, "left")
        total += count_all_descendants(child, "right")

    return total


# ----------------------------------------------------------
# Binary + Eligibility + Flashout calculation
# ----------------------------------------------------------
def calculate_binary(member, left_today, right_today, left_cf, right_cf):
    L = left_today + left_cf
    R = right_today + right_cf

    result = {
        "new_binary_eligible": member.binary_eligible,
        "eligibility_income": Decimal("0"),
        "binary_income": Decimal("0"),
        "flashout_income": Decimal("0"),
        "left_cf_after": L,
        "right_cf_after": R,
    }

    eligibility_triggered_today = False

    # -------------------------------
    # Eligibility check (first time)
    # -------------------------------
    if not member.binary_eligible:
        if (L >= 2 and R >= 1) or (L >= 1 and R >= 2):
            result["new_binary_eligible"] = True
            result["eligibility_income"] = ELIGIBILITY_BONUS
            eligibility_triggered_today = True

            # Deduct the eligibility pair from counts (lock the unpaired used)
            if L >= 2 and R >= 1:
                L -= 2
                R -= 1
            else:
                L -= 1
                R -= 2

    # -------------------------------
    # Daily binary income
    # -------------------------------
    pairs = min(L, R)

    # If eligibility happened today, only 4 paid pairs allowed (not 5)
    daily_limit = DAILY_BINARY_PAIR_LIMIT
    if eligibility_triggered_today:
        daily_limit = 4  # eligibility pair counted as first, but not paid

    paid_pairs = min(pairs, daily_limit)
    result["binary_income"] = paid_pairs * PAIR_VALUE

    L -= paid_pairs
    R -= paid_pairs

    # -------------------------------
    # Flashout
    # -------------------------------
    remaining_pairs = pairs - paid_pairs
    flash_units = min(remaining_pairs // FLASHOUT_GROUP_SIZE, MAX_DAILY_FLASHOUTS)
    result["flashout_income"] = flash_units * FLASHOUT_VALUE

    L -= flash_units * FLASHOUT_GROUP_SIZE
    R -= flash_units * FLASHOUT_GROUP_SIZE

    result["left_cf_after"] = L
    result["right_cf_after"] = R

    return result


# ----------------------------------------------------------
# Run engine for ONE member
# ----------------------------------------------------------
@transaction.atomic
def run_binary_engine(member, run_date=None):
    if not run_date:
        run_date = timezone.now().date()

    report, _ = DailyIncomeReport.objects.get_or_create(
        member=member,
        date=run_date,
        defaults={
            "binary_income": Decimal("0"),
            "binary_eligibility_income": Decimal("0"),
            "sponsor_income": Decimal("0"),
            "flashout_wallet_income": Decimal("0"),
            "total_income": Decimal("0"),
            "left_cf": 0,
            "right_cf": 0,
        }
    )

    left_today = count_all_descendants(member, "left")
    right_today = count_all_descendants(member, "right")

    res = calculate_binary(
        member,
        left_today,
        right_today,
        report.left_cf,
        report.right_cf,
    )

    report.binary_income = res["binary_income"]
    report.binary_eligibility_income = res["eligibility_income"]
    report.flashout_wallet_income = res["flashout_income"]
    report.left_cf = res["left_cf_after"]
    report.right_cf = res["right_cf_after"]

    report.total_income = (
        report.binary_income
        + report.binary_eligibility_income
        + report.flashout_wallet_income
        + report.sponsor_income
    )

    report.save()

    if res["new_binary_eligible"] and not member.binary_eligible:
        member.binary_eligible = True
        member.save(update_fields=["binary_eligible"])

    return report


# ----------------------------------------------------------
# Run engine for ALL members (daily)
# ----------------------------------------------------------
@transaction.atomic
def run_daily_engine(run_date=None):
    if not run_date:
        run_date = timezone.now().date()

    for member in Member.objects.filter(is_active=True).order_by("id"):
        run_binary_engine(member, run_date)

