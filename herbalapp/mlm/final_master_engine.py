# ==========================================================
# Final Corrected MLM Master Engine
# ==========================================================
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from herbalapp.models import Member, DailyIncomeReport


# -------------------------------
# CONSTANTS / RULES
# -------------------------------
PAIR_VALUE = Decimal("500")  # Binary income per pair
ELIGIBILITY_BONUS = Decimal("500")  # One-time eligibility bonus
DAILY_BINARY_LIMIT = 5  # Max binary pairs per normal day
ELIGIBILITY_DAY_MAX_PAIRS = 4  # Max binary pairs on eligibility day
FLASHOUT_UNIT_PAIRS = 5  # 1 flashout unit = 5 pairs
MAX_FLASHOUT_UNITS = 9  # Max flashout units per day
ROOT_ID = "rocky001"


# -------------------------------
# FULL TREE DOWNLINE COUNT
# -------------------------------
def count_full_downline(member, side):
    """
    Count full downline (direct + indirect) for a given side.
    """
    if not member:
        return 0

    children = Member.objects.filter(parent=member, side=side, is_active=True)
    total = children.count()
    for child in children:
        total += count_full_downline(child, "left")
        total += count_full_downline(child, "right")
    return total


# -------------------------------
# HELPER: Calculate member binary & eligibility income
# -------------------------------
def calculate_member_binary_income(left_today, right_today, left_cf, right_cf, binary_eligible, is_eligibility_day=False):
    """
    left_today / right_today: today's new joins
    left_cf / right_cf: carry forward from previous days
    binary_eligible: member's eligibility flag
    is_eligibility_day: if today is first eligibility day
    Returns: dict with binary_income, eligibility_income, flashout, CFs, total
    """
    L = left_today + left_cf
    R = right_today + right_cf
    eligibility_income = Decimal("0")
    binary_income = Decimal("0")
    flashout_income = Decimal("0")
    flashout_units = 0
    new_binary_eligible = binary_eligible

    # -------------------------------
    # 1️⃣ ELIGIBILITY INCOME
    # -------------------------------
    if is_eligibility_day:
        eligibility_income = ELIGIBILITY_BONUS
        new_binary_eligible = True
        # Binary income max 4 pairs on eligibility day
        pairs_today = min(L, R, ELIGIBILITY_DAY_MAX_PAIRS)
        binary_income = pairs_today * PAIR_VALUE
        L -= pairs_today
        R -= pairs_today
    else:
        # Normal day binary income (for eligible members)
        if binary_eligible:
            pairs_today = min(L, R, DAILY_BINARY_LIMIT)
            binary_income = pairs_today * PAIR_VALUE
            L -= pairs_today
            R -= pairs_today

    # -------------------------------
    # 2️⃣ FLASHOUT BONUS
    # -------------------------------
    remaining_pairs = min(L, R)
    flashout_units = min(remaining_pairs // FLASHOUT_UNIT_PAIRS, MAX_FLASHOUT_UNITS)
    flashout_income = flashout_units * Decimal("1000")
    used_pairs = flashout_units * FLASHOUT_UNIT_PAIRS
    L -= used_pairs
    R -= used_pairs

    # -------------------------------
    # RETURN RESULTS
    # -------------------------------
    total_income = binary_income + eligibility_income + flashout_income

    return {
        "binary_income": binary_income,
        "eligibility_income": eligibility_income,
        "flashout_income": flashout_income,
        "flashout_units": flashout_units,
        "new_binary_eligible": new_binary_eligible,
        "left_cf_after": L,
        "right_cf_after": R,
        "total_income": total_income,
    }


# -------------------------------
# MASTER DAILY ENGINE
# -------------------------------
@transaction.atomic
def run_full_daily_engine(run_date=None):
    """
    Full daily engine:
    1. Calculate eligibility & binary for all members
    2. Credit sponsor income if eligible
    3. Update DailyIncomeReport
    """
    if not run_date:
        run_date = timezone.localdate()

    print(f"\n🚀 Running Full Daily MLM Engine for {run_date}\n")

    members = Member.objects.exclude(auto_id=ROOT_ID).order_by("id")

    # -------------------------------
    # 1️⃣ Calculate binary & eligibility
    # -------------------------------
    for member in members:

        # Get or create DailyIncomeReport
        report, _ = DailyIncomeReport.objects.get_or_create(
            member=member,
            date=run_date,
            defaults={
                "binary_income": 0,
                "binary_eligibility_income": 0,
                "sponsor_income": 0,
                "flashout_wallet_income": 0,
                "total_income": 0,
                "left_cf": 0,
                "right_cf": 0,
                "sponsor_processed": False,
            }
        )

        # Check eligibility (full tree moment-based)
        left_full = count_full_downline(member, "left")
        right_full = count_full_downline(member, "right")
        is_eligibility_day = False
        if not member.binary_eligible:
            if (left_full >= 2 and right_full >= 1) or (left_full >= 1 and right_full >= 2):
                member.binary_eligible = True
                member.binary_eligible_date = run_date
                member.save(update_fields=["binary_eligible", "binary_eligible_date"])
                is_eligibility_day = True
                print(f"✅ {member.auto_id} completed BINARY ELIGIBILITY")

        # Today's joins
        left_today = Member.objects.filter(
            placement_id = member.placement.id if member.placement else None,
            side="left",
            joined_date=run_date,
            is_active=True
        ).count()
        right_today = Member.objects.filter(
            placement_id = member.placement.id if member.placement else None,
            side="right",
            joined_date=run_date,
            is_active=True
        ).count()

        # Calculate binary, eligibility, flashout
        res = calculate_member_binary_income(
            left_today=left_today,
            right_today=right_today,
            left_cf=report.left_cf,
            right_cf=report.right_cf,
            binary_eligible=member.binary_eligible,
            is_eligibility_day=is_eligibility_day
        )

        # Update report
        report.binary_income = res["binary_income"]
        report.binary_eligibility_income = res["eligibility_income"]
        report.flashout_wallet_income = res["flashout_income"]
        report.left_cf = res["left_cf_after"]
        report.right_cf = res["right_cf_after"]
        report.total_income = (
            res["binary_income"] +
            res["eligibility_income"] +
            res["flashout_income"] +
            report.sponsor_income
        )
        report.save()

    # -------------------------------
    # 2️⃣ Sponsor Income (Rule-based)
    # -------------------------------
    for child in members:
        child_report = DailyIncomeReport.objects.get(member=child, date=run_date)
        if child_report.sponsor_processed:
            continue

        sponsor = None

        # Rule 1 & 2: determine who is sponsor
        if child.placement_id == child.sponsor_id:
            if child.placement and child.placement.parent and child.placement.parent.auto_id != ROOT_ID:
                sponsor = child.placement.parent
        else:
            if child.sponsor and child.sponsor.auto_id != ROOT_ID:
                sponsor = child.sponsor

        if sponsor:
            # Rule 3: sponsor must have completed 1:1 pair under legs
            left_pairs = count_full_downline(sponsor, "left")
            right_pairs = count_full_downline(sponsor, "right")
            if left_pairs >= 1 and right_pairs >= 1:
                # Only child's binary + eligibility income counts
                sponsor_amount = Decimal(
                    (child_report.binary_eligibility_income or 0) +
                    (child_report.binary_income or 0)
                )

                if sponsor_amount > 0:
                    sponsor_report, _ = DailyIncomeReport.objects.get_or_create(
                        member=sponsor,
                        date=run_date,
                        defaults={
                            "binary_income": 0,
                            "binary_eligibility_income": 0,
                            "sponsor_income": 0,
                            "flashout_wallet_income": 0,
                            "total_income": 0,
                        }
                    )

                    sponsor_report.sponsor_income += sponsor_amount
                    sponsor_report.total_income = (
                        sponsor_report.binary_income +
                        sponsor_report.binary_eligibility_income +
                        sponsor_report.flashout_wallet_income +
                        sponsor_report.sponsor_income
                    )
                    sponsor_report.save(update_fields=["sponsor_income", "total_income"])

                    sponsor.sponsor_income += sponsor_amount
                    sponsor.main_wallet += sponsor_amount
                    sponsor.save(update_fields=["sponsor_income", "main_wallet"])

                    print(f"✅ Sponsor {sponsor.auto_id} credited {sponsor_amount} from child {child.auto_id}")

        child_report.sponsor_processed = True
        child_report.save(update_fields=["sponsor_processed"])

    # -------------------------------
    # 3️⃣ Safety Recalculate Total
    # -------------------------------
    for report in DailyIncomeReport.objects.filter(date=run_date):
        report.total_income = (
            (report.binary_income or 0) +
            (report.binary_eligibility_income or 0) +
            (report.flashout_wallet_income or 0) +
            (report.sponsor_income or 0)
        )
        report.save()

    print(f"\n🔥 Full Daily MLM Engine completed for {run_date}\n")


