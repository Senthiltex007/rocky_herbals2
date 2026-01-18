# ==========================================================
# herbalapp/management/commands/mlm_run_full_daily.py
# ==========================================================
from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from django.db import transaction

from herbalapp.models import Member, DailyIncomeReport

ROOT_ID = "rocky004"

# ----------------------------------------------------------
# Binary & Flashout calculation
# ----------------------------------------------------------
def calculate_member_binary_income_for_day(
    left_joins_today,
    right_joins_today,
    left_cf_before,
    right_cf_before,
    binary_eligible
):
    PAIR_VALUE = Decimal("500")
    ELIGIBILITY_BONUS = Decimal("500")
    DAILY_BINARY_PAIR_LIMIT = 5

    L = left_joins_today + left_cf_before
    R = right_joins_today + right_cf_before

    new_binary_eligible = binary_eligible
    eligibility_income = Decimal("0")
    binary_pairs_paid = 0
    binary_income = Decimal("0")

    # 1️⃣ Binary eligibility (2:1 or 1:2)
    if not binary_eligible and ((L >= 2 and R >= 1) or (L >= 1 and R >= 2)):
        new_binary_eligible = True
        eligibility_income = ELIGIBILITY_BONUS

        # Deduct eligibility pair counts
        if L >= 2 and R >= 1:
            L -= 2
            R -= 1
        else:
            L -= 1
            R -= 2

        # -------------------------------
        # Eligibility day → binary income max 4 pairs only
        # -------------------------------
        total_pairs_available = min(L, R)
        binary_pairs_paid = min(total_pairs_available, 4)  # max 4 pairs on eligibility day
        binary_income = binary_pairs_paid * PAIR_VALUE

        # Deduct binary pairs used
        L -= binary_pairs_paid
        R -= binary_pairs_paid

        # -------------------------------
        # Flashout from remaining pairs
        # -------------------------------
        pairs_remaining_after_binary = total_pairs_available - binary_pairs_paid
        flashout_units = min(pairs_remaining_after_binary // 5, 9)  # 1 flashout unit = 5 pairs, max 9 units/day
        flashout_pairs_used = flashout_units * 5
        flashout_income = flashout_units * 1000

        # Deduct flashout pairs
        L -= flashout_pairs_used
        R -= flashout_pairs_used

        # -------------------------------
        # Washout
        # -------------------------------
        washed_pairs = pairs_remaining_after_binary - flashout_pairs_used

        # -------------------------------
        # Total income for child report (eligibility + binary + flashout)
        # -------------------------------
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
    # 2️⃣ NORMAL DAYS → AFTER ELIGIBLE (MAX 5 PAIRS)
    # -------------------------------
    total_pairs_available = min(L, R)

    binary_pairs_paid = min(total_pairs_available, DAILY_BINARY_PAIR_LIMIT)
    binary_income = binary_pairs_paid * PAIR_VALUE

    L -= binary_pairs_paid
    R -= binary_pairs_paid

    # -------------------------------
    # FLASHOUT BONUS
    # -------------------------------
    pairs_remaining_after_binary = total_pairs_available - binary_pairs_paid

    flashout_units = min(pairs_remaining_after_binary // 5, 9)
    flashout_pairs_used = flashout_units * 5
    flashout_income = flashout_units * Decimal("1000")

    L -= flashout_pairs_used
    R -= flashout_pairs_used

    # -------------------------------
    # WASHOUT
    # -------------------------------
    washed_pairs = pairs_remaining_after_binary - flashout_pairs_used

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

# ----------------------------------------------------------
# Sponsor Receiver (Rule 1 & Rule 2)
# ----------------------------------------------------------
def get_sponsor_receiver(child: Member):
    if not child.sponsor:
        return None

    # Dummy/root never earns
    if child.sponsor.auto_id == ROOT_ID:
        return None

    # Rule 1: placement == sponsor → placement parent
    if child.placement_id == child.sponsor_id:
        if child.placement and child.placement.parent:
            if child.placement.parent.auto_id != ROOT_ID:
                return child.placement.parent
        return None

    # Rule 2: placement != sponsor → sponsor directly
    return child.sponsor

# ----------------------------------------------------------
# Rule 3: Sponsor must have direct left & right child
# ----------------------------------------------------------
def can_receive_sponsor_income(sponsor: Member):
    left = 1 if sponsor.left_child() else 0
    right = 1 if sponsor.right_child() else 0
    return left >= 1 and right >= 1

# ----------------------------------------------------------
# FULL DAILY ENGINE
# ----------------------------------------------------------
@transaction.atomic
def run_full_daily_engine(run_date: date):

    members = Member.objects.exclude(auto_id=ROOT_ID).order_by("id")

    # 1️⃣ Binary + Eligibility
    for member in members:

        report, _ = DailyIncomeReport.objects.get_or_create(
            member=member,
            date=run_date
        )

        # reset daily values
        report.binary_income = Decimal("0.00")
        report.binary_eligibility_income = Decimal("0.00")
        report.sponsor_income = Decimal("0.00")
        report.total_income = Decimal("0.00")
        report.sponsor_processed = False   # ✅ VERY IMPORTANT (daily reset)

        # ✅ TODAY joins (DO NOT subtract CF)
        left_today = 1 if member.left_child() else 0
        right_today = 1 if member.right_child() else 0

        res = calculate_member_binary_income_for_day(
            left_today,
            right_today,
            report.left_cf,
            report.right_cf,
            member.binary_eligible
        )

        # ✅ Binary income only if real 1:1 pair happened
        if res.get("binary_pairs_paid", 0) > 0:
            report.binary_income = res["binary_income"]
        else:
            report.binary_income = Decimal("0.00")

        # 🔧 FIX: No real 1:1 pair → move wrongly credited binary to sponsor base
        if res.get("binary_pairs_paid", 0) == 0 and res.get("binary_income", Decimal("0")) > 0:
            report.binary_income = Decimal("0.00")
            # amount will be picked by sponsor engine via eligibility/binary fields

        # ✅ Eligibility bonus credited to child report only
        report.binary_eligibility_income = res["eligibility_income"]

        # ✅ Carry-forward update
        report.left_cf = res["left_cf_after"]
        report.right_cf = res["right_cf_after"]

        report.save()

        # ✅ Update member binary eligibility flag
        if res["new_binary_eligible"] and not member.binary_eligible:
            member.binary_eligible = True
            member.save(update_fields=["binary_eligible"])
            print(f"✅ {member.member_id} is now binary eligible and credited ₹500 eligibility bonus")

    # =============================
    # 2️⃣ Sponsor Income (Child-Based)
    # =============================
    for child in members:

        child_report = DailyIncomeReport.objects.get(
            member=child,
            date=run_date
        )

        if child_report.sponsor_processed:
            continue

        sponsor = get_sponsor_receiver(child)

        if not sponsor:
            child_report.sponsor_processed = True
            child_report.save(update_fields=["sponsor_processed"])
            continue

        # sponsor income = child eligibility + child binary income
        sponsor_amount = (
            (child_report.binary_eligibility_income or Decimal("0")) +
            (child_report.binary_income if child_report.binary_income > 0 else Decimal("0"))
        )

        if sponsor_amount > 0 and can_receive_sponsor_income(sponsor):

            sponsor_report, _ = DailyIncomeReport.objects.get_or_create(
                member=sponsor,
                date=run_date
            )

            sponsor_report.sponsor_income += sponsor_amount
            sponsor_report.total_income += sponsor_amount
            sponsor_report.save(update_fields=["sponsor_income", "total_income"])

            print(f"✅ Sponsor {sponsor.member_id} credited {sponsor_amount} from child {child.member_id}")

        else:
            print(f"⚠️ Sponsor {sponsor.member_id if sponsor else 'None'} skipped: child {child.member_id} had no sponsor income")

        # always mark processed
        child_report.sponsor_processed = True
        child_report.save(update_fields=["sponsor_processed"])

    # =============================
    # 3️⃣ Final Total
    # =============================
    for report in DailyIncomeReport.objects.filter(date=run_date):
        report.total_income = (
            (report.binary_income or Decimal("0")) +
            (report.binary_eligibility_income or Decimal("0")) +
            (report.sponsor_income or Decimal("0"))
        )
        report.save(update_fields=["total_income"])

# ----------------------------------------------------------
# Django Management Command
# ----------------------------------------------------------
class Command(BaseCommand):
    help = "Run FULL MLM Daily Engine (Binary + Sponsor)"

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, help="YYYY-MM-DD")

    def handle(self, *args, **options):
        run_date = parse_date(options["date"]) if options.get("date") else date.today()
        self.stdout.write(f"🚀 Running MLM Engine for {run_date}")

        try:
            run_full_daily_engine(run_date)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
            return

        self.stdout.write(self.style.SUCCESS("✅ MLM Daily Engine Completed"))

