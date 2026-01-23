# ==========================================================
# herbalapp/mlm_engine_binary_runner.py
# ==========================================================
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport

PAIR_VALUE = Decimal("500")
ELIGIBILITY_BONUS = Decimal("500")
DAILY_BINARY_PAIR_LIMIT = 5
FLASHOUT_GROUP_SIZE = 5
FLASHOUT_VALUE = 1000
MAX_DAILY_FLASHOUTS = 9


def count_all_descendants(member):
    if not member:
        return 0

    # Find left and right children using parent+side
    left_child = Member.objects.filter(parent=member, side='L').first()
    right_child = Member.objects.filter(parent=member, side='R').first()

    left_count = count_all_descendants(left_child) if left_child else 0
    right_count = count_all_descendants(right_child) if right_child else 0

    # Count this member + descendants
    return 1 + left_count + right_count
def calculate_binary(member, left_today, right_today, left_cf, right_cf):
    """
    Calculates binary, eligibility, flashout incomes
    """
    L = left_today + left_cf
    R = right_today + right_cf

    new_binary_eligible = member.binary_eligible
    # eligibility_income init removed (using result dict)
    binary_pairs_paid = 0
    binary_income = Decimal("0")
    flashout_units = 0
    flashout_pairs_used = 0
    flashout_income = Decimal("0")
    washed_pairs = 0

    # -------------------------------
    # Eligibility check
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
            binary_pairs_paid = min(total_pairs_available, DAILY_BINARY_PAIR_LIMIT)
            binary_income = washed_pairs * PAIR_VALUE
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
    binary_income = washed_pairs * PAIR_VALUE
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


@transaction.atomic
def run_binary_engine(member, run_date=None):
    """
    Run binary & eligibility engine for a member and return daily report
    """
    if not run_date:
        run_date = timezone.now().date()

    report, _ = DailyIncomeReport.objects.get_or_create(member=member, date=run_date)

    left_today = count_all_descendants(Member.objects.filter(parent=member, side='L').first())
    right_today = count_all_descendants(Member.objects.filter(parent=member, side='R').first())

    res = calculate_binary(member, left_today, right_today, report.left_cf, report.right_cf)

    # ✅ Safe Decimal assignment
    report.binary_income = res.get("binary_income", Decimal("0"))
    report.binary_eligibility_income = res.get("result[\"eligibility_income\"]", Decimal("0"))
    report.flashout_units = res.get("flashout_units", 0)
    report.left_cf = res.get("left_cf_after", 0)
    report.right_cf = res.get("right_cf_after", 0)
    report.total_income = (
        (report.binary_income or Decimal("0"))
        + (report.binary_eligibility_income or Decimal("0"))
        + (report.sponsor_income or Decimal("0"))
    )
    report.save()

    if res["new_binary_eligible"] and not member.binary_eligible:
        member.binary_eligible = True
        member.save(update_fields=["binary_eligible"])

    return report


@transaction.atomic
def run_daily_engine(run_date=None):
    """
    Run engine for all active members
    """
    if not run_date:
        run_date = timezone.now().date()

    members = Member.objects.filter(is_active=True).order_by("id")

    for member in members:
        run_binary_engine(member, run_date)

