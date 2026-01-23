# ==========================================================
# herbalapp/mlm_engine_daily.py
# ==========================================================
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport

ROOT_ID = "rocky001"
PAIR_VALUE = Decimal("500")
ELIGIBILITY_BONUS = Decimal("500")
DAILY_BINARY_PAIR_LIMIT = 5
FLASHOUT_PAIR_UNIT = 5
FLASHOUT_UNIT_VALUE = 1000
MAX_FLASHOUT_UNITS = 9


def count_all_descendants(member, side=None):
    """
    Recursively count all descendants optionally by side
    """
    if not member:
        return 0

    count = 0
    if side:
        children = Member.objects.filter(parent=member, side=side, is_active=True)
        for child in children:
            count += 1 + count_all_descendants(child)
    else:
        children = Member.objects.filter(parent=member, is_active=True)
        for child in children:
            count += 1 + count_all_descendants(child)

    return count


def calculate_binary(member, left_today, right_today, left_cf, right_cf):
    """
    Calculate eligibility, binary, flashout income
    """
    L = left_today + left_cf
    R = right_today + right_cf

    new_binary_eligible = member.binary_eligible
    eligibility_income = Decimal("0")
    binary_pairs_paid = 0
    binary_income = Decimal("0")
    flashout_units = 0
    flashout_pairs_used = 0
    flashout_income = Decimal("0")
    washed_pairs = 0

    # -------------------------------
    # Eligibility check (1:2 or 2:1)
    # -------------------------------
    if not member.binary_eligible:
        if (L >= 2 and R >= 1) or (L >= 1 and R >= 2):
            new_binary_eligible = True
            eligibility_income = ELIGIBILITY_BONUS

            # Deduct first eligibility pair
            if L >= 2 and R >= 1:
                L -= 2
                R -= 1
            else:
                L -= 1
                R -= 2

            # Binary income on eligibility day (max 4 pairs extra)
            total_pairs_available = min(L, R)
            binary_pairs_paid = min(total_pairs_available, 4)
            binary_income = binary_pairs_paid * PAIR_VALUE
            L -= binary_pairs_paid
            R -= binary_pairs_paid

            # Flashout bonus
            remaining_pairs = total_pairs_available - binary_pairs_paid
            flashout_units = min(remaining_pairs // FLASHOUT_PAIR_UNIT, MAX_FLASHOUT_UNITS)
            flashout_pairs_used = flashout_units * FLASHOUT_PAIR_UNIT
            flashout_income = flashout_units * FLASHOUT_UNIT_VALUE
            L -= flashout_pairs_used
            R -= flashout_pairs_used

            washed_pairs = remaining_pairs - flashout_pairs_used

            total_income = eligibility_income + binary_income + flashout_income

            return {
                "new_binary_eligible": new_binary_eligible,
                "eligibility_income": eligibility_income,
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
    # Normal day (already eligible)
    # -------------------------------
    total_pairs_available = min(L, R)
    binary_pairs_paid = min(total_pairs_available, DAILY_BINARY_PAIR_LIMIT)
    binary_income = binary_pairs_paid * PAIR_VALUE
    L -= binary_pairs_paid
    R -= binary_pairs_paid

    remaining_pairs = total_pairs_available - binary_pairs_paid
    flashout_units = min(remaining_pairs // FLASHOUT_PAIR_UNIT, MAX_FLASHOUT_UNITS)
    flashout_pairs_used = flashout_units * FLASHOUT_PAIR_UNIT
    flashout_income = flashout_units * FLASHOUT_UNIT_VALUE
    L -= flashout_pairs_used
    R -= flashout_pairs_used

    washed_pairs = remaining_pairs - flashout_pairs_used
    total_income = binary_income + flashout_income

    return {
        "new_binary_eligible": new_binary_eligible,
        "eligibility_income": eligibility_income,
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


def get_sponsor_receiver(child):
    """
    Rule 1,2,3: Return the correct sponsor to credit income
    """
    if not child.sponsor:
        return None
    if child.sponsor.auto_id == ROOT_ID:
        return None

    # Rule 1: placement == sponsor → placement.parent
    if child.placement_id == child.sponsor_id:
        if child.placement and child.placement.parent and child.placement.parent.auto_id != ROOT_ID:
            return child.placement.parent
        return None
    # Rule 2: placement != sponsor → sponsor
    return child.sponsor


def can_receive_sponsor_income(sponsor):
    """
    Rule 3: must have at least 1:1 (left+right) to get sponsor income
    """
    return bool(sponsor.left_child() and sponsor.right_child())


@transaction.atomic
def run_binary_engine(member, run_date=None):
    """
    Run binary & eligibility engine + flashout for a member
    """
    if not run_date:
        run_date = timezone.now().date()

    report, _ = DailyIncomeReport.objects.get_or_create(member=member, date=run_date)

    # Today joins count (correct)
    left_today = Member.objects.filter(parent=member, side='L', joined_date=run_date, is_active=True).count()
    right_today = Member.objects.filter(parent=member, side='R', joined_date=run_date, is_active=True).count()

    res = calculate_binary(member, left_today, right_today, report.left_cf, report.right_cf)

    report.binary_income = res.get("binary_income", Decimal("0"))
    report.binary_eligibility_income = res.get("eligibility_income", Decimal("0"))
    report.flashout_wallet_income = res.get("flashout_income", Decimal("0"))
    report.left_cf = res.get("left_cf_after", 0)
    report.right_cf = res.get("right_cf_after", 0)
    report.total_income = (
        report.binary_income + report.binary_eligibility_income + report.flashout_wallet_income + report.sponsor_income
    )
    report.save()

    # Mark binary eligible
    if res["new_binary_eligible"] and not member.binary_eligible:
        member.binary_eligible = True
        member.save(update_fields=["binary_eligible"])

    return report


@transaction.atomic
def run_daily_engine(run_date=None):
    """
    Run engine for all members (binary + sponsor)
    """
    if not run_date:
        run_date = timezone.now().date()

    members = Member.objects.filter(is_active=True).order_by("id")

    # 1️⃣ Run binary + eligibility + flashout
    for member in members:
        run_binary_engine(member, run_date)

    # 2️⃣ Sponsor income (Rule 1,2,3)
    for child in members:
        child_report = DailyIncomeReport.objects.get(member=child, date=run_date)

        if (child_report.binary_income == 0 and child_report.binary_eligibility_income == 0):
            continue
        if child_report.sponsor_processed:
            continue

        sponsor = get_sponsor_receiver(child)

        if not sponsor or sponsor.auto_id == ROOT_ID:
            child_report.sponsor_processed = True
            child_report.save(update_fields=["sponsor_processed"])
            continue

        # Rule 3: must have 1:1
        if not (sponsor.left_child() and sponsor.right_child()):
            child_report.sponsor_processed = True
            child_report.save(update_fields=["sponsor_processed"])
            continue

        sponsor_amount = child_report.binary_income + child_report.binary_eligibility_income
        if sponsor_amount > 0:
            sponsor_report, _ = DailyIncomeReport.objects.get_or_create(member=sponsor, date=run_date)
            sponsor_report.sponsor_income += sponsor_amount
            sponsor_report.total_income = (
                sponsor_report.binary_income
                + sponsor_report.binary_eligibility_income
                + sponsor_report.flashout_wallet_income
                + sponsor_report.sponsor_income
            )
            sponsor_report.save()

            sponsor.sponsor_income += sponsor_amount
            sponsor.main_wallet += sponsor_amount
            sponsor.save(update_fields=["sponsor_income", "main_wallet"])

        child_report.sponsor_processed = True
        child_report.save(update_fields=["sponsor_processed"])

    # 3️⃣ Final total update
    for report in DailyIncomeReport.objects.filter(date=run_date):
        report.total_income = (
            report.binary_income
            + report.binary_eligibility_income
            + report.flashout_wallet_income
            + report.sponsor_income
        )
        report.save()

