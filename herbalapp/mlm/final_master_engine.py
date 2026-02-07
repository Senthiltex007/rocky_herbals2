# ==========================================================
# herbalapp/management/commands/mlm_run_full_daily.py
# ==========================================================
from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from django.db import transaction, IntegrityError
from django.utils import timezone
from herbalapp.mlm.engine_lock import run_with_lock
from datetime import date, timedelta

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

from datetime import date, timedelta
from herbalapp.models import Member

# ------------------------------------------------------------
# Helper: Count all descendants including direct children
# (DATE AWARE – VERY IMPORTANT)
# ------------------------------------------------------------
def count_all_descendants(member, side, as_of_date=None):
    """
    member: Member object
    side: 'left' or 'right'
    as_of_date: date or None
    Returns total descendants count including direct children (as of date)
    """
    if not member:
        return 0

    qs = Member.objects.filter(parent=member, side=side)
    if as_of_date is not None:
        qs = qs.filter(joined_date__lte=as_of_date)

    total = 0
    for child in qs:
        total += 1
        total += count_all_descendants(child, "left", as_of_date=as_of_date)
        total += count_all_descendants(child, "right", as_of_date=as_of_date)

    return total

def is_direct_sponsor_eligible(member, run_date):
    """
    Sponsor eligibility rule (LIFETIME):
    DIRECT 1:1 must exist (one direct left + one direct right).
    Binary eligibility (1:2/2:1) is NOT required here.
    """

    # If you have methods:
    left = member.left_child() if callable(getattr(member, "left_child", None)) else None
    right = member.right_child() if callable(getattr(member, "right_child", None)) else None

    # Fallback (model-safe) if methods not available:
    if left is None:
        left = Member.objects.filter(parent=member, side="left").order_by("id").first()
    if right is None:
        right = Member.objects.filter(parent=member, side="right").order_by("id").first()

    if not left or not right:
        return False

    # Optional safety: only consider active members (if your model has is_active)
    if hasattr(left, "is_active") and not left.is_active:
        return False
    if hasattr(right, "is_active") and not right.is_active:
        return False

    return True

# =============================================================
# MLM Engine: Print member tree + left/right descendant counts
# (DEBUG / VERIFY ONLY – NO INCOME CREDIT HERE)
# =============================================================
def run_mlm_engine(run_date):
    print("=" * 120)
    print("FULL MEMBER TREE + TODAY JOIN COUNTS (SAFE DEBUG)")
    print("=" * 120)

    yesterday = run_date - timedelta(days=1)

    members = Member.objects.filter(
        is_active=True,
        joined_date__lte=run_date
    ).order_by("auto_id")

    for m in members:

        # Totals as of today
        left_today_total = count_all_descendants(m, "left", as_of_date=run_date)
        right_today_total = count_all_descendants(m, "right", as_of_date=run_date)

        # Totals as of yesterday
        left_yday_total = count_all_descendants(m, "left", as_of_date=yesterday)
        right_yday_total = count_all_descendants(m, "right", as_of_date=yesterday)

        # TODAY joins (delta)
        left_joins_today = max(left_today_total - left_yday_total, 0)
        right_joins_today = max(right_today_total - right_yday_total, 0)

        # Binary eligibility check (LIFETIME, based on totals)
        binary_eligible = (
            (left_today_total >= 2 and right_today_total >= 1) or
            (left_today_total >= 1 and right_today_total >= 2)
        )

        print("MEMBER ID            :", m.auto_id)
        print("Name                 :", m.name)
        print("Active               :", m.is_active)
        print("Binary Eligible      :", binary_eligible)
        print("Sponsor ID           :", m.sponsor.auto_id if m.sponsor else None)
        print("Parent ID            :", m.parent.auto_id if m.parent else None)
        print("Placement Side       :", m.side)
        print("LEFT TOTAL DESC      :", left_today_total)
        print("RIGHT TOTAL DESC     :", right_today_total)
        print("LEFT JOINS TODAY     :", left_joins_today)
        print("RIGHT JOINS TODAY    :", right_joins_today)
        print("Joined Date          :", m.joined_date)
        print("-" * 60)

    print("=" * 120)
    print("MLM ENGINE DEBUG RUN COMPLETE ✅")
    print("=" * 120)


# =============================================================
# Force run daily function (PRODUCTION SAFE)
# =============================================================
def force_run_daily(run_date):
    """
    Force run the FULL production MLM engine for given date.

    ✅ Uses run_full_daily_engine (PRODUCTION)
    ✅ Engine itself handles:
       - today joins only
       - no duplicate binary
       - no duplicate sponsor
       - no income if no joins today
    """

    print(f"⚡ Force running FULL MLM Engine for {run_date}")
    print(f"🚀 Running MLM Master Engine for {run_date}")

    try:
        run_full_daily_engine(run_date)
    except Exception as e:
        print(f"❌ Error while running MLM Engine: {str(e)}")
    else:
        print(f"✅ MLM Engine run completed successfully for {run_date}")


# =============================================================
# Example: Run for specific date (MANUAL DEBUG)
# =============================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        run_date = date.fromisoformat(sys.argv[1])
    else:
        run_date = date.today()

    force_run_daily(run_date)

# ----------------------------------------------------------
# Binary & Flashout calculation (RULE-ACCURATE & PURE)
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
    🔹 Binary & Flashout daily calculation (FINAL)

    RULES IMPLEMENTED:
    ✅ Eligibility: 1:2 or 2:1 → eligibility_income = 500
    ✅ Eligibility day:
        - 1:2 / 2:1 counted as FIRST PAIR (LOCKED)
        - NO binary income for that first pair
        - Max 4 binary pairs allowed that day
        - Total max = 500 + (4 * 500) = 2500
    ✅ Normal day:
        - Max 5 binary pairs/day
    ✅ Flashout:
        - 5 pairs = 1 unit = 1000
        - Max 9 units/day
        - Goes to wallet only (NOT sponsor, NOT cash)
    ✅ Carry forward:
        - Unpaired members move forward lifetime
    """

    # -----------------------------------
    # 🔹 CF + today join calculation
    # -----------------------------------
    L = int(left_today) + int(left_cf_before)
    R = int(right_today) + int(right_cf_before)

    eligibility_income = Decimal("0")
    binary_pairs_paid = 0
    binary_income = Decimal("0")
    flashout_units = 0
    flashout_income = Decimal("0")
    washed_pairs = 0

    # ==================================================
    # 0️⃣ NOT ELIGIBLE YET → ONLY FLASHOUT (NO BINARY)
    # ==================================================
    if not binary_eligible and not became_binary_eligible_today:
        remaining_pairs = min(L, R)

        flashout_units = min(
            remaining_pairs // FLASHOUT_PAIR_UNIT,
            MAX_FLASHOUT_UNITS
        )
        flashout_income = flashout_units * Decimal("1000")
        used_pairs = flashout_units * FLASHOUT_PAIR_UNIT

        L -= used_pairs
        R -= used_pairs
        washed_pairs = remaining_pairs - used_pairs

        return {
            "new_binary_eligible": False,
            "eligibility_income": Decimal("0"),
            "binary_pairs_paid": 0,
            "binary_income": Decimal("0"),
            "flashout_units": flashout_units,
            "flashout_pairs_used": used_pairs,
            "flashout_income": flashout_income,
            "washed_pairs": washed_pairs,
            "left_cf_after": L,
            "right_cf_after": R,
            "total_income": Decimal("0"),  # cash only
        }

    # ==================================================
    # 1️⃣ ELIGIBILITY DAY (1:2 or 2:1 REACHED TODAY)
    # ==================================================
    if became_binary_eligible_today:
        eligibility_income = ELIGIBILITY_BONUS  # 500

        # 🔒 Consume eligibility pair (LOCKED)
        if L >= 2 and R >= 1:
            L -= 2
            R -= 1
        elif L >= 1 and R >= 2:
            L -= 1
            R -= 2

        # Remaining pairs eligible for binary income (MAX 4)
        available_pairs = min(L, R)
        binary_pairs_paid = min(available_pairs, DAILY_BINARY_PAIR_LIMIT - 1)  # 4
        binary_income = Decimal(binary_pairs_paid) * PAIR_VALUE

        L -= binary_pairs_paid
        R -= binary_pairs_paid

        # Flashout after binary income
        remaining_pairs = min(L, R)
        flashout_units = min(
            remaining_pairs // FLASHOUT_PAIR_UNIT,
            MAX_FLASHOUT_UNITS
        )
        flashout_income = flashout_units * Decimal("1000")
        used_pairs = flashout_units * FLASHOUT_PAIR_UNIT

        L -= used_pairs
        R -= used_pairs
        washed_pairs = remaining_pairs - used_pairs

        return {
            "new_binary_eligible": True,
            "eligibility_income": eligibility_income,
            "binary_pairs_paid": binary_pairs_paid,
            "binary_income": binary_income,
            "flashout_units": flashout_units,
            "flashout_pairs_used": used_pairs,
            "flashout_income": flashout_income,
            "washed_pairs": washed_pairs,
            "left_cf_after": L,
            "right_cf_after": R,
            "total_income": eligibility_income + binary_income,  # cash only
        }

    # ==================================================
    # 2️⃣ NORMAL DAY (ALREADY ELIGIBLE)
    # ==================================================
    total_pairs = min(L, R)

    # ✅ Normal day: pay from available pairs (CF + today joins), max 5 pairs/day
    binary_pairs_paid = min(total_pairs, DAILY_BINARY_PAIR_LIMIT)  # 5
    binary_income = Decimal(binary_pairs_paid) * PAIR_VALUE

    L -= binary_pairs_paid
    R -= binary_pairs_paid

    # Flashout after binary income
    remaining_pairs = min(L, R)
    flashout_units = min(
        remaining_pairs // FLASHOUT_PAIR_UNIT,
        MAX_FLASHOUT_UNITS
    )
    flashout_income = flashout_units * Decimal("1000")
    used_pairs = flashout_units * FLASHOUT_PAIR_UNIT

    L -= used_pairs
    R -= used_pairs
    washed_pairs = remaining_pairs - used_pairs

    return {
        "new_binary_eligible": True,
        "eligibility_income": Decimal("0"),
        "binary_pairs_paid": binary_pairs_paid,
        "binary_income": binary_income,
        "flashout_units": flashout_units,
        "flashout_pairs_used": used_pairs,
        "flashout_income": flashout_income,
        "washed_pairs": washed_pairs,
        "left_cf_after": L,
        "right_cf_after": R,
        "total_income": binary_income,  # cash only
    }

# ----------------------------------------------------------
# Sponsor calculation rules (DIRECT 1:1 LIFETIME)
# ----------------------------------------------------------
def can_receive_sponsor_income(member: Member, run_date) -> bool:
    """
    Sponsor eligibility = DIRECT 1:1 (lifetime)
    - Direct left child exists AND direct right child exists (as of run_date)
    """
    if not member:
        return False

    left_exists = Member.objects.filter(
        parent=member, side="left", is_active=True, joined_date__lte=run_date
    ).exists()

    right_exists = Member.objects.filter(
        parent=member, side="right", is_active=True, joined_date__lte=run_date
    ).exists()

    return left_exists and right_exists


def get_sponsor_receiver(child: Member, run_date):
    """
    Rule-1: placement_id == sponsor_id -> placement gets sponsor income
    Rule-2: placement_id != sponsor_id -> sponsor gets sponsor income
    ROOT never receives sponsor income
    Receiver must satisfy DIRECT 1:1 (as of run_date)
    """
    if not child:
        return None

    placement_id = getattr(child, "placement_id", None)
    sponsor_id = getattr(child, "sponsor_id", None)

    if placement_id and sponsor_id and placement_id == sponsor_id:
        receiver = getattr(child, "placement", None) or getattr(child, "parent", None)
    else:
        receiver = getattr(child, "sponsor", None)

    if not receiver or receiver.auto_id == ROOT_ID:
        return None

    if not can_receive_sponsor_income(receiver, run_date):
        return None

    return receiver


# ==========================================================
# FULL DAILY ENGINE (RE-RUN SAFE)
# ==========================================================
def run_full_daily_engine(run_date: date):
    """
    ✅ FULL DAILY ENGINE (LOCKED)

    - Uses EngineLock (is_running + finished_at)
    - Allows rerun only for TODAY with cooldown (late join fix)
    - Sets EngineLock.finished_at after successful run
    """

    def _engine(run_date: date):
        # ✅ YOUR EXISTING ENGINE CODE STARTS HERE (UNCHANGED)
        print(f"🚀 Running MLM Master Engine for {run_date}")

        yesterday_date = run_date - timedelta(days=1)

        # --------------------------------------------------
        # ✅ RE-RUN SAFE: reset ONLY that day's reports
        # --------------------------------------------------
        DailyIncomeReport.objects.filter(date=run_date).update(
            eligibility_income=Decimal("0.00"),
            binary_eligibility_income=Decimal("0.00"),
            binary_income=Decimal("0.00"),
            sponsor_income=Decimal("0.00"),
            flashout_wallet_income=Decimal("0.00"),
            total_income=Decimal("0.00"),
            earned_fresh_binary_today=False,
            sponsor_today_processed=False,
            binary_income_processed=False,
            total_income_locked=False,
            binary_pairs_paid=0,
            flashout_units=0,
            washed_pairs=0,
        )

        members = Member.objects.filter(
            is_active=True,
            joined_date__lte=run_date
        ).order_by("auto_id")

        # ==================================================
        # 1) BINARY + ELIGIBILITY + FLASHOUT + CF
        # ==================================================
        for member in members:

            # ROOT: never gets any income; still keep report row
            if member.auto_id == ROOT_ID:
                report, _ = DailyIncomeReport.objects.get_or_create(
                    date=run_date,
                    member=member,
                    defaults={
                        "left_cf": 0,
                        "right_cf": 0,
                    }
                )
                report.binary_income_processed = True
                report.sponsor_today_processed = True
                report.total_income_locked = True
                report.save(update_fields=[
                    "binary_income_processed",
                    "sponsor_today_processed",
                    "total_income_locked",
                ])
                print(f"⛔ {member.auto_id} skipped (ROOT dummy)")
                continue

            # ✅ ONE PLACE ONLY: get_or_create (no try/except duplicate)
            report, _ = DailyIncomeReport.objects.get_or_create(
                date=run_date,
                member=member,
                defaults={
                    "left_cf": 0,
                    "right_cf": 0,
                    "sponsor_today_processed": False,
                    "binary_income_processed": False,
                }
            )

            # Yesterday report for CF
            yesterday_report = DailyIncomeReport.objects.filter(
                date=yesterday_date,
                member=member
            ).first()

            left_cf_before = int(yesterday_report.left_cf) if yesterday_report else 0
            right_cf_before = int(yesterday_report.right_cf) if yesterday_report else 0

            report.left_cf_before = left_cf_before
            report.right_cf_before = right_cf_before

            # Today totals vs yesterday totals (date-aware)
            left_total_today = count_all_descendants(member, "left", as_of_date=run_date)
            right_total_today = count_all_descendants(member, "right", as_of_date=run_date)

            left_total_yday = count_all_descendants(member, "left", as_of_date=yesterday_date)
            right_total_yday = count_all_descendants(member, "right", as_of_date=yesterday_date)

            # Today joins (pure delta)
            left_today = max(left_total_today - left_total_yday, 0)
            right_today = max(right_total_today - right_total_yday, 0)

            report.left_joins = left_today
            report.right_joins = right_today

            # --------------------------------------------------
            # ✅ NEWLY REACHED ELIGIBILITY TODAY ONLY
            # (supports rerun: if eligible_date == run_date -> treat as became today)
            # --------------------------------------------------
            eligible_today = (
                (left_total_today >= 2 and right_total_today >= 1) or
                (left_total_today >= 1 and right_total_today >= 2)
            )
            eligible_yday = (
                (left_total_yday >= 2 and right_total_yday >= 1) or
                (left_total_yday >= 1 and right_total_yday >= 2)
            )

            # -----------------------------------------
            # ✅ Deterministic eligibility logic
            # -----------------------------------------
            existing_date = getattr(member, "binary_eligible_date", None)

            # If eligible today, member is lifetime eligible (set True)
            if eligible_today and not member.binary_eligible:
                member.binary_eligible = True

            # Decide "became eligible today" purely by counts:
            # eligible_today True AND eligible_yday False AND
            # (never eligible before OR first eligible is today)
            became_binary_eligible_today = (
                eligible_today
                and (not eligible_yday)
                and (existing_date is None or existing_date == run_date)
            )

            # If member first time eligible (existing_date is None), set earliest eligible date
            # If some bad run wrote a later date, keep the earliest date
            if eligible_today:
                if (
                    existing_date is None
                    or (
                        hasattr(existing_date, "date")
                        and existing_date.date() > run_date
                    )
                    or (
                        isinstance(existing_date, date)
                        and existing_date > run_date
                    )
                ):
                    member.binary_eligible_date = run_date

            # ✅ Save member only if fields changed
            member.save(update_fields=["binary_eligible", "binary_eligible_date"])

            # Report snapshot
            report.binary_eligible = member.binary_eligible

            # --------------------------------------------------
            # ✅ If not eligible (and not became today) -> no binary cash
            # --------------------------------------------------
            if not (member.binary_eligible or became_binary_eligible_today):
                # still allow flashout via calculate() (it returns cash 0)
                res = calculate_member_binary_income_for_day(
                    member,
                    left_today=left_today,
                    right_today=right_today,
                    left_cf_before=left_cf_before,
                    right_cf_before=right_cf_before,
                    binary_eligible=False,
                    became_binary_eligible_today=False
                )

                report.flashout_wallet_income = res["flashout_income"]
                report.left_cf = res["left_cf_after"]
                report.right_cf = res["right_cf_after"]
                report.left_cf_after = report.left_cf
                report.right_cf_after = report.right_cf

                report.binary_income_processed = True
                report.total_income = Decimal("0.00")
                report.save(update_fields=[
                    "flashout_wallet_income",
                    "left_cf",
                    "right_cf",
                    "left_cf_after",
                    "right_cf_after",
                    "binary_income_processed",
                    "total_income",
                ])

                print(f"⛔ {member.auto_id} skipped binary income (not eligible)")
                continue

            # --------------------------------------------------
            # ✅ Eligible: calculate using TODAY joins + CF
            # If NO joins today AND not eligibility day -> just keep CF, no binary
            # --------------------------------------------------
            if left_today == 0 and right_today == 0 and not became_binary_eligible_today:
                report.left_cf = left_cf_before
                report.right_cf = right_cf_before
                report.left_cf_after = report.left_cf
                report.right_cf_after = report.right_cf
                report.binary_income_processed = True
                report.total_income = Decimal("0.00")
                report.save(update_fields=[
                    "left_cf",
                    "right_cf",
                    "left_cf_after",
                    "right_cf_after",
                    "binary_income_processed",
                    "total_income",
                ])
                continue

            res = calculate_member_binary_income_for_day(
                member,
                left_today=left_today,
                right_today=right_today,
                left_cf_before=left_cf_before,
                right_cf_before=right_cf_before,
                binary_eligible=member.binary_eligible,
                became_binary_eligible_today=became_binary_eligible_today
            )

            with transaction.atomic():
                report.eligibility_income = res["eligibility_income"]
                report.binary_eligibility_income = res["eligibility_income"]  # mirror for sponsor

                report.binary_income = res["binary_income"]
                report.binary_pairs_paid = res["binary_pairs_paid"]

                report.flashout_wallet_income = res["flashout_income"]
                report.flashout_units = res["flashout_units"]
                report.washed_pairs = res["washed_pairs"]

                report.left_cf = res["left_cf_after"]
                report.right_cf = res["right_cf_after"]
                report.left_cf_after = report.left_cf
                report.right_cf_after = report.right_cf

                report.earned_fresh_binary_today = (
                    (report.binary_income > 0) or (report.binary_eligibility_income > 0)
                )

                # Sponsor income will be added later
                report.total_income = report.eligibility_income + report.binary_income

                report.binary_income_processed = True

                report.save(update_fields=[
                    "eligibility_income",
                    "binary_eligibility_income",
                    "binary_income",
                    "binary_pairs_paid",
                    "flashout_wallet_income",
                    "flashout_units",
                    "washed_pairs",
                    "left_cf",
                    "right_cf",
                    "left_cf_after",
                    "right_cf_after",
                    "earned_fresh_binary_today",
                    "total_income",
                    "binary_income_processed",
                ])

        # ==================================================
        # 2️⃣ SPONSOR INCOME – DIRECT 1:1 ELIGIBLE RECEIVER
        # ==================================================
        sponsor_children = list(get_valid_sponsor_children(run_date))

        print("🧾 SPONSOR CHILDREN TODAY:", [c.auto_id for c in sponsor_children])

        for child in sponsor_children:

            if child.auto_id == ROOT_ID:
                continue

            child_report = DailyIncomeReport.objects.filter(
                member=child,
                date=run_date
            ).first()
            if not child_report:
                continue

            # 🔍 DEBUG: child mapping (before receiver decide)
            print(
                "\n👶 CHILD:", child.auto_id,
                "| placement_id:", getattr(child, "placement_id", None),
                "| sponsor_id:", getattr(child, "sponsor_id", None),
                "| parent:", child.parent.auto_id if getattr(child, "parent", None) else None,
                "| sponsor:", child.sponsor.auto_id if getattr(child, "sponsor", None) else None
            )

            # ✅ Receiver based on Rule-1/Rule-2 + DIRECT 1:1 eligibility
            receiver = get_sponsor_receiver(child, run_date)
            print("🎯 RECEIVER:", receiver.auto_id if receiver else None)

            if not receiver:
                continue

            # ✅ Child-level lock (duplicate safe)
            updated = DailyIncomeReport.objects.filter(
                member=child,
                date=run_date,
                sponsor_today_processed=False
            ).update(sponsor_today_processed=True)

            print("🔒 CHILD LOCK UPDATED:", updated)

            if updated == 0:
                continue

            sponsor_amount = child_report.binary_income + child_report.binary_eligibility_income
            print("💰 CHILD AMOUNT:", child_report.binary_income, "+", child_report.binary_eligibility_income, "=", sponsor_amount)

            if sponsor_amount <= 0:
                continue

            with transaction.atomic():
                receiver_report, _ = DailyIncomeReport.objects.get_or_create(
                    member=receiver,
                    date=run_date
                )
                receiver_report.sponsor_income += sponsor_amount
                receiver_report.total_income += sponsor_amount
                receiver_report.save(update_fields=["sponsor_income", "total_income"])

                print("✅ CREDITED TO:", receiver.auto_id, "| sponsor_income now:", receiver_report.sponsor_income)

        # ==================================================
        # 3) FINAL TOTAL LOCK
        # ==================================================
        for report in DailyIncomeReport.objects.filter(date=run_date):
            if report.total_income_locked:
                continue

            report.total_income = (
                (report.binary_income or Decimal("0.00")) +
                (report.binary_eligibility_income or Decimal("0.00")) +
                (report.sponsor_income or Decimal("0.00"))
            )
            report.total_income_locked = True
            report.save(update_fields=["total_income", "total_income_locked"])

        print("✅ MLM Master Engine Completed Successfully")
        # ✅ YOUR EXISTING ENGINE CODE ENDS HERE (UNCHANGED)

    # ✅ IMPORTANT: run through global lock wrapper
    return run_with_lock(run_date, _engine, allow_rerun_today=True, cooldown_minutes=5)

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
