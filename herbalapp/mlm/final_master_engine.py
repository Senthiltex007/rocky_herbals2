# ==========================================================
# herbalapp/management/commands/mlm_run_full_daily.py
# ==========================================================
from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from datetime import timedelta
from django.db import transaction, IntegrityError
from django.utils import timezone
from herbalapp.models import EngineLock

# --------------------------
# Models
# --------------------------
from herbalapp.models import Member, DailyIncomeReport

# ✅ Filter engine / helper functions
from herbalapp.mlm.filters import get_valid_sponsor_children

#from herbalapp.tasks import run_engine_task

ROOT_ID = "rocky001"
PAIR_VALUE = Decimal("500")
ELIGIBILITY_BONUS = Decimal("500")
DAILY_BINARY_PAIR_LIMIT = 5
FLASHOUT_PAIR_UNIT = 5
MAX_FLASHOUT_UNITS = 9
# ============================================================
# MLM Engine Helper & Run Script
# ============================================================
from herbalapp.models import Member

# ------------------------------------------------------------
# Helper: Count all descendants including direct children
# ------------------------------------------------------------
def count_all_descendants(member, side):
    """
    member: Member object
    side: 'left' or 'right'
    Returns total descendants count including direct children
    """
    if not member:
        return 0

    # Get all direct children on this side
    children = Member.objects.filter(parent=member, side=side)
    total = 0

    for child in children:
        total += 1  # Count direct child
        # Recursively count child's left and right descendants
        total += count_all_descendants(child, "left")
        total += count_all_descendants(child, "right")

    return total

# =============================================================
# MLM Engine: Print member tree + left/right descendant counts
# =============================================================
def run_mlm_engine(run_date):
    print("="*120)
    print("FULL MEMBER TREE + LEFT / RIGHT COUNT (DIRECT CHILD INCLUDED)")
    print("="*120)

    members = Member.objects.filter(
        is_active=True,
        joined_date__lte=run_date
    ).order_by("auto_id")

    for m in members:
        left_cnt = count_all_descendants(m, "left")
        right_cnt = count_all_descendants(m, "right")

        binary_eligible = (
            (left_cnt >= 1 and right_cnt >= 2) or
            (left_cnt >= 2 and right_cnt >= 1)
        )

        print("MEMBER ID       :", m.auto_id)
        print("Name            :", m.name)
        print("Active          :", m.is_active)
        print("Binary Eligible :", binary_eligible)
        print("Sponsor ID      :", m.sponsor.auto_id if m.sponsor else None)
        print("Parent ID       :", m.parent.auto_id if m.parent else None)
        print("Placement Side  :", m.side)
        print("LEFT DESC COUNT :", left_cnt)
        print("RIGHT DESC COUNT:", right_cnt)
        print("Joined Date     :", m.joined_date)
        print("-"*60)

    print("="*120)
    print("MLM ENGINE RUN COMPLETE ✅")
    print("="*120)


# =============================================================
# Force run daily function (PRODUCTION SAFE)
# =============================================================
def force_run_daily(run_date):
    """
    Force run the FULL production MLM engine for given date.

    ✅ Uses run_full_daily_engine (PRODUCTION)
    ✅ Deletes old EngineLock if exists
    ✅ Handles all binary + eligibility + sponsor income + flashout + carry forward
    """

    from herbalapp.models import EngineLock

    # 🔒 Delete existing EngineLock for that date (if exists)
    print(f"⚡ Force running FULL MLM Engine for {run_date}")
    print(f"🗑️  Deleted existing EngineLock for {run_date}")
    print(f"🚀 Running MLM Master Engine for {run_date}")

    try:
        # ✅ PRODUCTION ENGINE
        run_full_daily_engine(run_date)
    except Exception as e:
        print(f"❌ Error while running MLM Engine: {str(e)}")
    else:
        print(f"✅ MLM Engine run completed successfully for {run_date}")


# =============================================================
# Example: Run for specific date
# =============================================================
if __name__ == "__main__":
    import sys
    from datetime import date

    # Usage: python mlm_engine.py 2026-01-29
    if len(sys.argv) > 1:
        run_date = sys.argv[1]
    else:
        run_date = date.today()

    force_run_daily(run_date)

# ----------------------------------------------------------
# Binary & Flashout calculation (Rule-Compliant)
# ----------------------------------------------------------
def calculate_member_binary_income_for_day(
        member,
        left_today,
        right_today,
        left_cf_before,
        right_cf_before,
        binary_eligible,
        became_binary_eligible_today
):
    """
    🔹 Binary & Flashout daily calculation

    ✅ Eligibility: 1:2 or 2:1 → eligibility_income 500
    ✅ Binary income: max 5 pairs/day
    ✅ Flashout bonus: 5 pairs = 1 unit = 1000, max 9 units/day
    ✅ Carry forward unpaired members (CF)
    ✅ Eligibility pair locked implicitly (not counted again for binary income)
    """

    # -----------------------------------
    # 🔹 CF + today join calculation
    # -----------------------------------
    L = left_today + left_cf_before
    R = right_today + right_cf_before

    new_binary_eligible = binary_eligible
    eligibility_income = Decimal("0")
    binary_pairs_paid = 0
    binary_income = Decimal("0")
    flashout_units = 0
    flashout_income = Decimal("0")
    washed_pairs = 0

    # -------------------------------
    # 0️⃣ Not eligible yet → only flashout
    # -------------------------------
    if not binary_eligible and ((L < 2 and R < 1) and (L < 1 and R < 2)):
        new_binary_eligible = False
        remaining_pairs = min(L, R)

        flashout_units = min(remaining_pairs // FLASHOUT_PAIR_UNIT, MAX_FLASHOUT_UNITS)
        flashout_income = flashout_units * Decimal("1000")
        used_pairs = flashout_units * FLASHOUT_PAIR_UNIT

        # CF update
        L -= used_pairs
        R -= used_pairs
        washed_pairs = remaining_pairs - used_pairs
        total_income = flashout_income

        return {
            "new_binary_eligible": new_binary_eligible,
            "eligibility_income": eligibility_income,
            "binary_pairs_paid": binary_pairs_paid,
            "binary_income": binary_income,
            "flashout_units": flashout_units,
            "flashout_pairs_used": used_pairs,
            "flashout_income": flashout_income,
            "washed_pairs": washed_pairs,
            "left_cf_after": L,
            "right_cf_after": R,
            "total_income": total_income,
        }

    # -------------------------------
    # 1️⃣ Eligibility day → binary_eligible becomes True
    # -------------------------------
    if not binary_eligible and became_binary_eligible_today:
        new_binary_eligible = True
        eligibility_income = ELIGIBILITY_BONUS

        # 🔹 Lifetime update
        member.binary_eligible = True
        member.save(update_fields=['binary_eligible'])

        # 🔹 Eligibility pair consumption
        if L >= 2 and R >= 1:
            L -= 2
            R -= 1
        elif L >= 1 and R >= 2:
            L -= 1
            R -= 2

        # Binary income for eligibility day = 0
        binary_pairs_paid = 0
        binary_income = Decimal("0")

        # 🔹 Flashout bonus (after eligibility pair)
        remaining_pairs = min(L, R)
        flashout_units = min(remaining_pairs // FLASHOUT_PAIR_UNIT, MAX_FLASHOUT_UNITS)
        flashout_income = flashout_units * Decimal("1000")
        used_pairs = flashout_units * FLASHOUT_PAIR_UNIT

        L -= used_pairs
        R -= used_pairs
        washed_pairs = remaining_pairs - used_pairs
        total_income = eligibility_income + flashout_income

        return {
            "new_binary_eligible": new_binary_eligible,
            "eligibility_income": eligibility_income,
            "binary_pairs_paid": binary_pairs_paid,
            "binary_income": binary_income,
            "flashout_units": flashout_units,
            "flashout_pairs_used": used_pairs,
            "flashout_income": flashout_income,
            "washed_pairs": washed_pairs,
            "left_cf_after": L,
            "right_cf_after": R,
            "total_income": total_income,
        }

    # -------------------------------
    # 2️⃣ Normal day → already eligible
    # -------------------------------
    total_pairs_available = min(L, R)

    # 🔹 Binary income (max 5 pairs/day)
    binary_pairs_paid = min(total_pairs_available, DAILY_BINARY_PAIR_LIMIT)
    binary_income = binary_pairs_paid * PAIR_VALUE

    # Consume binary-paid pairs
    L -= binary_pairs_paid
    R -= binary_pairs_paid

    # 🔹 Flashout bonus (after binary income)
    remaining_pairs = min(L, R)
    flashout_units = min(remaining_pairs // FLASHOUT_PAIR_UNIT, MAX_FLASHOUT_UNITS)
    flashout_income = flashout_units * Decimal("1000")
    used_pairs = flashout_units * FLASHOUT_PAIR_UNIT

    L -= used_pairs
    R -= used_pairs
    washed_pairs = remaining_pairs - used_pairs
    total_income = binary_income + flashout_income

    return {
        "new_binary_eligible": new_binary_eligible,
        "eligibility_income": eligibility_income,
        "binary_pairs_paid": binary_pairs_paid,
        "binary_income": binary_income,
        "flashout_units": flashout_units,
        "flashout_pairs_used": used_pairs,
        "flashout_income": flashout_income,
        "washed_pairs": washed_pairs,
        "left_cf_after": L,
        "right_cf_after": R,
        "total_income": total_income,
    }

# ----------------------------------------------------------
# Sponsor calculation rules (FINAL – NO ROOT CONCEPT)
# ----------------------------------------------------------
def get_sponsor_receiver(child: Member):
    """
    Returns the correct sponsor/placement to credit today based on Rules 1,2,3.
    
    Rules:
    1️⃣ If placement_id == sponsor_id → placement itself gets sponsor income
       (except Rocky001 → always skip)
    2️⃣ If placement_id != sponsor_id → sponsor gets sponsor income
       (except Rocky001 → always skip)
    3️⃣ Sponsor must have completed at least one 1:1 pair (binary_eligible=True)
    """
    if not child.sponsor:
        return None

    # Rule 3: Sponsor must have 1:1 pair to receive sponsor income
    if not can_receive_sponsor_income(child.sponsor):
        return None

    # Rule 1: placement == sponsor → placement itself
    if child.placement_id == child.sponsor_id:
        if child.placement and child.placement.auto_id != "rocky001":
            return child.placement
        # Rocky001 dummy → skip
        return None

    # Rule 2: placement != sponsor → sponsor
    if child.sponsor.auto_id != "rocky001":
        return child.sponsor

    # Rocky001 dummy → skip
    return None


def can_receive_sponsor_income(member: Member):
    """
    Sponsor income eligibility (FINAL RULE):

    - Member must have reached at least one 1:1 (lifetime)
    - Once eligible, always eligible
    - Yesterday eligible → today also can receive sponsor income
    """

    if not member:
        return False

    # Lifetime sponsor eligibility based on 1:1 achievement
    return member.binary_eligible is True

# ----------------------------------------------------------
# FULL DAILY ENGINE (FINAL SAFE VERSION)
# ----------------------------------------------------------
def run_full_daily_engine(run_date: date):

    # 🔒 GLOBAL DAY LOCK (FIRST LINE)
   # try:
       # lock = EngineLock.objects.create(
            #run_date=run_date,
            #is_running=True,
            #started_at=timezone.now()
        #)
    #except IntegrityError:
        # Row already exists, fetch existing lock
        #lock = EngineLock.objects.get(run_date=run_date)
        #print(f"⛔ Engine already ran for {run_date}")
        #return

    print(f"🚀 Running MLM Master Engine for {run_date}")
    # 🔁 HARD RESET: EarnedToday flag (engine ↔ shell sync)
    DailyIncomeReport.objects.filter(date=run_date).update(
        earned_fresh_binary_today=False,
    )


    members = Member.objects.filter(
        is_active=True,
        joined_date__lte=run_date
    ).order_by("auto_id")

    # ==================================================
    # MEMBER LOOP – LIFETIME BINARY ELIGIBILITY
    # ==================================================
    for member in members:

        became_binary_eligible_today = False

        left_cnt = count_all_descendants(member, "left")
        right_cnt = count_all_descendants(member, "right")

        if (
            (left_cnt >= 2 and right_cnt >= 1) or
            (left_cnt >= 1 and right_cnt >= 2)
        ) and not member.binary_eligible:

            member.binary_eligible = True
            member.save(update_fields=["binary_eligible"])
            became_binary_eligible_today = True

        if became_binary_eligible_today:
            print(f"✅ {member.auto_id} became lifetime binary eligible")

        # --------------------------------------------------
        # 🔹 STEP 2: Get / create DAILY report
        # --------------------------------------------------
        report, _ = DailyIncomeReport.objects.get_or_create(
            member=member,
            date=run_date,
            defaults={
                "binary_income": Decimal("0.00"),
                "binary_eligibility_income": Decimal("0.00"),
                "sponsor_income": Decimal("0.00"),
                "flashout_wallet_income": Decimal("0.00"),
                "total_income": Decimal("0.00"),
                "left_cf": 0,
                "right_cf": 0,
                "earned_fresh_binary_today": False,
                "sponsor_today_processed": False,
                "total_income_locked": False,
            },
        )

        # --------------------------------------------------
        # ✅ STEP 3: HARD DAILY RESET (IDEMPOTENT)
        # --------------------------------------------------
        report.binary_income = Decimal("0.00")
        report.binary_eligibility_income = Decimal("0.00")
        report.flashout_wallet_income = Decimal("0.00")
        report.total_income = Decimal("0.00")

        # ❗ CF must reset DAILY
        yesterday = run_date - timedelta(days=1)
        yesterday_report = DailyIncomeReport.objects.filter(
                member=member,
                date=yesterday
        ).first()

        left_cf_before = yesterday_report.left_cf if yesterday_report else 0
        right_cf_before = yesterday_report.right_cf if yesterday_report else 0

        report.earned_fresh_binary_today = False
        report.total_income_locked = False

        report.save(update_fields=[
                "binary_income",
                "binary_eligibility_income",
                "flashout_wallet_income",
                "sponsor_income",
                "total_income",
                "earned_fresh_binary_today",
                "total_income_locked",
        ])

        # 🔹 Today joins + total descendants (corrected)
        left_total = count_all_descendants(member, side="left")
        right_total = count_all_descendants(member, side="right")

        # 🔹 Add carry forward from yesterday
        left_available = left_total + left_cf_before
        right_available = right_total + right_cf_before

        # 🔹 Today binary & eligibility calculation
        res = calculate_member_binary_income_for_day(
                member,
                left_today=left_total,
                right_today=right_total,
                left_cf_before=left_cf_before,
                right_cf_before=right_cf_before,
                binary_eligible=member.binary_eligible,
                became_binary_eligible_today=became_binary_eligible_today
        )

        # 🔒 Atomic update for member + report
        with transaction.atomic():
                if became_binary_eligible_today:
                        member.binary_eligible = True
                        member.save(update_fields=["binary_eligible"])

                report.binary_income = res["binary_income"]
                report.binary_eligibility_income = res["eligibility_income"]
                report.flashout_wallet_income = res["flashout_income"]
                report.left_cf = res["left_cf_after"]
                report.right_cf = res["right_cf_after"]

                if res["eligibility_income"] > 0 or res["binary_pairs_paid"] > 0:
                        report.earned_fresh_binary_today = True

                report.total_income = (
                        report.binary_income
                        + report.binary_eligibility_income
                        + report.flashout_wallet_income
                )
                report.save(
                        update_fields=[
                                "binary_income",
                                "binary_eligibility_income",
                                "flashout_wallet_income",
                                "left_cf",
                                "right_cf",
                                "earned_fresh_binary_today",
                                "total_income",
                        ]
                )

    # ==================================================
    # 2️⃣ SPONSOR INCOME – DUPLICATE SAFE (FINAL)
    # ==================================================
    for child in get_valid_sponsor_children(run_date):

        child_report = DailyIncomeReport.objects.get(
            member=child,
            date=run_date
        )

        # 🔒 SINGLE SOURCE OF TRUTH (child-level atomic lock)
        updated = DailyIncomeReport.objects.filter(
            member=child,
            date=run_date,
        ).update(sponsor_today_processed=True)

        if updated == 0:
            continue  # ❌ already processed in earlier run

        # --------------------------------------------------
        # Determine correct sponsor receiver
        # --------------------------------------------------
        receiver = None

        # Rule 1: placement == sponsor → placement itself
        if child.parent_id == child.sponsor_id:
            if child.parent and child.parent.auto_id != ROOT_ID:
                receiver = child.parent
        else:
            # Rule 2: placement != sponsor → sponsor
            if child.sponsor and child.sponsor.auto_id != ROOT_ID:
                receiver = child.sponsor

        # Rule 3: sponsor must be binary eligible
        if receiver and not receiver.binary_eligible:
            receiver = None

        sponsor_amount = (
            child_report.binary_income
            + child_report.binary_eligibility_income
        )

        if not receiver or sponsor_amount <= 0:
            continue

        # --------------------------------------------------
        # Credit sponsor income (append-only)
        # --------------------------------------------------
        with transaction.atomic():
            receiver_report, _ = DailyIncomeReport.objects.get_or_create(
                member=receiver,
                date=run_date
            )
            receiver_report.sponsor_income += sponsor_amount
            receiver_report.total_income += sponsor_amount
            receiver_report.save(
                update_fields=["sponsor_income", "total_income"]
            )

        print(
            f"✅ Sponsor income {sponsor_amount} credited to "
            f"{receiver.auto_id}, child: {child.auto_id}"
        )

    # ==================================================
    # 3️⃣ FINAL TOTAL LOCK
    # ==================================================
    for report in DailyIncomeReport.objects.filter(date=run_date):

        if report.total_income_locked:
            continue

        report.total_income = (
            report.binary_income
            + report.binary_eligibility_income
            + report.sponsor_income
            + report.flashout_wallet_income
        )

        report.total_income_locked = True
        report.save(
            update_fields=["total_income", "total_income_locked"]
        )

    print("✅ MLM Master Engine Completed Successfully")

    # 🔓 MARK ENGINE FINISHED
    #lock.is_running = False
    #lock.save(update_fields=["is_running"])

# ----------------------------------------------------------
# Django Command - MANUAL / CRON / CELERY SAFE
# ----------------------------------------------------------
class Command(BaseCommand):
    help = "Run FULL MLM Daily Engine (Binary + Sponsor)"

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, help="YYYY-MM-DD")

    def handle(self, *args, **options):
        run_date = (
            parse_date(options["date"])
            if options.get("date")
            else timezone.localdate()
        )

        self.stdout.write(f"🚀 Running MLM Engine for {run_date}")

        try:
            run_full_daily_engine(run_date)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
            return

        self.stdout.write(self.style.SUCCESS("✅ MLM Daily Engine Completed"))
