# ==========================================================
# herbalapp/mlm/final_mlm_daily_engine.py
# ==========================================================
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from herbalapp.models import Member, DailyIncomeReport

ROOT_ID = "rocky004"

# ==========================================================
# Binary Engine (FINAL – SAFE)
# ==========================================================
def calculate_member_binary_income_for_day(left_today, right_today, left_cf, right_cf, binary_eligible):
    """
    Rocky Herbals MLM Binary Engine (FINAL SAFE)

    Rules:
    1) Binary eligibility: 1:2 or 2:1
    2) Eligibility bonus: 500
    3) Eligibility day binary: max 4 pairs
    4) Normal day binary: max 5 pairs
    5) Flashout: 5 pairs = 1 unit, max 9 units/day
    6) Carry forward unmatched pairs
    """

    PAIR_VALUE = 500
    ELIGIBILITY_BONUS = 500
    DAILY_PAIR_LIMIT = 5
    FLASHOUT_GROUP = 5
    FLASHOUT_VALUE = 1000
    MAX_FLASHOUT_UNITS = 9

    L = left_today + left_cf
    R = right_today + right_cf

    new_binary_eligible = binary_eligible
    eligibility_income = Decimal("0")
    binary_income = Decimal("0")
    flashout_units = 0
    flashout_income = Decimal("0")
    washed_pairs = 0
    eligibility_day = False

    eligibility_pairs_paid = 0
    binary_pairs_paid_normal = 0

    # --------------------------------------------------
    # 1️⃣ Eligibility Day Logic
    # --------------------------------------------------
    if not binary_eligible and ((L >= 2 and R >= 1) or (L >= 1 and R >= 2)):
        eligibility_day = True
        new_binary_eligible = True
        eligibility_income = ELIGIBILITY_BONUS

        # Deduct eligibility condition
        if L >= 2 and R >= 1:
            L -= 2
            R -= 1
        else:
            L -= 1
            R -= 2

        # Eligibility day binary (max 4 pairs)
        total_pairs_available = min(L, R)
        eligibility_pairs_paid = min(total_pairs_available, 4)
        eligibility_income += eligibility_pairs_paid * PAIR_VALUE

        L -= eligibility_pairs_paid
        R -= eligibility_pairs_paid

        # Flashout after eligibility binary
        remaining_pairs = total_pairs_available - eligibility_pairs_paid

        flashout_units = min(remaining_pairs // FLASHOUT_GROUP, MAX_FLASHOUT_UNITS)
        flashout_income = flashout_units * FLASHOUT_VALUE

        flashout_pairs_used = flashout_units * FLASHOUT_GROUP
        L -= flashout_pairs_used
        R -= flashout_pairs_used

        washed_pairs = remaining_pairs - flashout_pairs_used

    # --------------------------------------------------
    # 2️⃣ Normal Day Binary (ONLY if NOT eligibility day)
    # --------------------------------------------------
    if not eligibility_day:
        total_pairs_available = min(L, R)
        binary_pairs_paid_normal = min(total_pairs_available, DAILY_PAIR_LIMIT)
        binary_income = binary_pairs_paid_normal * PAIR_VALUE

        L -= binary_pairs_paid_normal
        R -= binary_pairs_paid_normal

        remaining_pairs = total_pairs_available - binary_pairs_paid_normal

        flashout_units = min(remaining_pairs // FLASHOUT_GROUP, MAX_FLASHOUT_UNITS)
        flashout_income = flashout_units * FLASHOUT_VALUE

        flashout_pairs_used = flashout_units * FLASHOUT_GROUP
        L -= flashout_pairs_used
        R -= flashout_pairs_used

        washed_pairs = remaining_pairs - flashout_pairs_used

    total_income = eligibility_income + binary_income + flashout_income

    return {
        "new_binary_eligible": new_binary_eligible,
        "eligibility_income": eligibility_income,
        "binary_pairs_paid": eligibility_pairs_paid if eligibility_day else binary_pairs_paid_normal,
        "binary_income": binary_income,
        "flashout_units": flashout_units,
        "flashout_income": flashout_income,
        "washed_pairs": washed_pairs,
        "left_cf_after": L,
        "right_cf_after": R,
        "total_income": total_income,
    }

"""
# ==========================================================
# Sponsor Engine
# ==========================================================
def get_sponsor_receiver(child: Member):
    if not child.sponsor:
        return None
    if child.sponsor.auto_id == ROOT_ID:
        return None

    # Rule 1: placement == sponsor → placement parent
    if child.placement_id == child.sponsor_id:
        if (
            child.placement
            and child.placement.parent
            and child.placement.parent.auto_id != ROOT_ID
        ):
            return child.placement.parent
        return None

    # Rule 2: placement != sponsor → sponsor directly
    return child.sponsor


def can_receive_sponsor_income(sponsor: Member):
    left = 1 if sponsor.left_child() else 0
    right = 1 if sponsor.right_child() else 0
    return left >= 1 and right >= 1
"""
# ==========================================================
# Full Daily Engine
# ==========================================================
@transaction.atomic
def run_full_daily_engine(run_date=None):
    if not run_date:
        run_date = timezone.localdate()

    members = Member.objects.exclude(auto_id=ROOT_ID).order_by("id")

    # -------------------------
    # 1️⃣ Binary + Eligibility
    # -------------------------
    for member in members:
        report, _ = DailyIncomeReport.objects.get_or_create(
            member=member, date=run_date
        )

        left_today = 1 if member.left_child() else 0
        right_today = 1 if member.right_child() else 0

        res = calculate_member_binary_income_for_day(
            left_today,
            right_today,
            report.left_cf,
            report.right_cf,
            member.binary_eligible,
        )

        report.binary_income = Decimal(res["binary_income"])
        report.binary_eligibility_income = Decimal(res["eligibility_income"])
        report.flashout_units = res["flashout_units"]
        report.left_cf = res["left_cf_after"]
        report.right_cf = res["right_cf_after"]


        report.save()

        if res["new_binary_eligible"] and not member.binary_eligible:
            member.binary_eligible = True
            member.save(update_fields=["binary_eligible"])

    """
    # -------------------------
    # 2️⃣ Sponsor Inincome
    # -------------------------
    for child in members:
        child_report = DailyIncomeReport.objects.get(member=child, date=run_date)

        sponsor = get_sponsor_receiver(child)
        if not sponsor:
            continue

        # Total sponsor amount = child's eligibility income + child's binary income
        sponsor_amount = (
            Decimal(child_report.binary_eligibility_income or 0) +
            Decimal(child_report.binary_income or 0)
        )

        # Sponsor can receive only if they have completed 1:1 pair
        if sponsor_amount > 0 and can_receive_sponsor_income(sponsor):
            sponsor_report, _ = DailyIncomeReport.objects.get_or_create(
                member=sponsor, date=run_date
            )
            sponsor_report.sponsor_income += sponsor_amount
            sponsor_report.total_income += sponsor_amount
            sponsor_report.save(update_fields=["sponsor_income", "total_income"]) """

    # -------------------------
    # 3️⃣ Final Total (SAFE)
    # -------------------------
    for report in DailyIncomeReport.objects.filter(date=run_date):
        report.total_income = (
            (report.binary_income or Decimal("0"))
            + (report.binary_eligibility_income or Decimal("0"))
            + (report.sponsor_income or Decimal("0"))
        )
        report.save(update_fields=["total_income"])

# ==========================================================
# Audit / Monitor (SAFE – Sponsor Disabled)
# ==========================================================
def audit_daily_income(run_date=None):
    if not run_date:
        run_date = timezone.localdate()

    summary = {
        "total_members": 0,
        "binary_missing": 0,
        "flashout_missing": 0,
        "total_mismatch": 0,
    }

    members = Member.objects.exclude(auto_id=ROOT_ID)
    summary["total_members"] = members.count()

    for m in members:
        try:
            report = DailyIncomeReport.objects.get(member=m, date=run_date)
        except DailyIncomeReport.DoesNotExist:
            summary["binary_missing"] += 1
            summary["flashout_missing"] += 1
            summary["total_mismatch"] += 1
            continue

        # Binary eligibility missing
        if m.binary_eligible and report.binary_eligibility_income <= 0:
            summary["binary_missing"] += 1

        # Binary income missing
        if m.binary_eligible and report.binary_income <= 0 and report.binary_eligibility_income > 0:
            summary["binary_missing"] += 1

        # Flashout missing
        if getattr(report, "flashout_units", 0) > 0:
            if (report.flashout_wallet_income or Decimal("0")) <= 0:
                summary["flashout_missing"] += 1

        # Total mismatch check
        total_calc = (
            (report.binary_eligibility_income or Decimal("0"))
            + (report.binary_income or Decimal("0"))
            + (report.flashout_wallet_income or Decimal("0"))
        )

        if total_calc != (report.total_income or Decimal("0")):
            summary["total_mismatch"] += 1

    return summary


def print_audit_summary(run_date=None):
    summary = audit_daily_income(run_date)
    print(f"📊 Audit for {run_date}: {summary}")

