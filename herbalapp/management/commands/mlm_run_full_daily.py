# ==========================================================
# herbalapp/management/commands/mlm_run_full_daily.py
# ==========================================================
from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport

ROOT_ID = "rocky001"
PAIR_VALUE = Decimal("500")
ELIGIBILITY_BONUS = Decimal("500")
DAILY_BINARY_PAIR_LIMIT = 5
FLASHOUT_PAIR_UNIT = 5
MAX_FLASHOUT_UNITS = 9

def count_all_descendants(member):
    if not member:
        return 0
    count = 1  # include this member
    if member.left_child():
        count += count_all_descendants(member.left_child())
    if member.right_child():
        count += count_all_descendants(member.right_child())
    return count


# ----------------------------------------------------------
# Binary & Flashout calculation (Corrected)
# ----------------------------------------------------------
def calculate_member_binary_income_for_day(left_today, right_today, left_cf_before, right_cf_before, binary_eligible):
    """
    Corrected MLM Binary + Eligibility Engine
    ✅ Binary eligibility check
    ✅ Eligibility day max 4 pairs
    ✅ Binary income calculation
    ✅ Flashout bonus calculation
    ✅ Leftover/washout pairs carry forward
    ✅ Eligibility pair locked
    ✅ Total income calculated
    ❌ Sponsor income untouched
    """

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
    # 0️⃣ Safety guard: if cannot become eligible
    # -------------------------------
    if not binary_eligible and ((L < 2 and R < 1) and (L < 1 and R < 2)):
        remaining_pairs = min(L, R)
        flashout_units = min(remaining_pairs // FLASHOUT_PAIR_UNIT, MAX_FLASHOUT_UNITS)
        flashout_income = flashout_units * Decimal("1000")
        used_pairs = flashout_units * FLASHOUT_PAIR_UNIT
        L -= used_pairs
        R -= used_pairs
        washed_pairs = remaining_pairs - used_pairs
        total_income = flashout_income
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
            "total_income": total_income,
        }

    # -------------------------------
    # 1️⃣ Eligibility Day: binary_eligible becomes True
    # -------------------------------
    if not binary_eligible and ((L >= 2 and R >= 1) or (L >= 1 and R >= 2)):
        # Eligibility bonus
        new_binary_eligible = True
        eligibility_income = ELIGIBILITY_BONUS

        # Deduct first pair (1:2 or 2:1)
        if L >= 2 and R >= 1:
            L -= 2
            R -= 1
        else:
            L -= 1
            R -= 2

        # Max 4 pairs for binary income on eligibility day
        total_pairs_available = min(L, R)
        binary_pairs_paid = min(total_pairs_available, 4)
        binary_income = binary_pairs_paid * PAIR_VALUE
        L -= binary_pairs_paid
        R -= binary_pairs_paid

        # Flashout bonus
        remaining_pairs = total_pairs_available - binary_pairs_paid
        flashout_units = min(remaining_pairs // FLASHOUT_PAIR_UNIT, MAX_FLASHOUT_UNITS)
        flashout_income = flashout_units * Decimal("1000")
        used_pairs = flashout_units * FLASHOUT_PAIR_UNIT
        L -= used_pairs
        R -= used_pairs

        washed_pairs = remaining_pairs - used_pairs
        total_income = eligibility_income + binary_income + flashout_income

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
    # 2️⃣ Normal Day: already eligible
    # -------------------------------
    total_pairs_available = min(L, R)
    binary_pairs_paid = min(total_pairs_available, DAILY_BINARY_PAIR_LIMIT)
    binary_income = binary_pairs_paid * PAIR_VALUE
    L -= binary_pairs_paid
    R -= binary_pairs_paid

    # Flashout bonus
    remaining_pairs = total_pairs_available - binary_pairs_paid
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
# Sponsor calculation rules (untouched)
# ----------------------------------------------------------
def get_sponsor_receiver(child: Member):
    if not child.sponsor:
        return None
    if child.sponsor.auto_id == ROOT_ID:
        return None
    if child.placement_id == child.sponsor_id:
        if (
            child.placement
            and child.placement.parent
            and child.placement.parent.auto_id != ROOT_ID
        ):
            return child.placement.parent
        return None
    return child.sponsor


def can_receive_sponsor_income(sponsor: Member):
    return bool(sponsor.left_child() and sponsor.right_child())
# ----------------------------------------------------------
# FULL DAILY ENGINE (untouched except binary calculation)
# ----------------------------------------------------------
@transaction.atomic
def run_full_daily_engine(run_date: date):
    members = Member.objects.exclude(auto_id=ROOT_ID).order_by("id")

    # ------------------------------------------------------
    # 1️⃣ Binary + Eligibility (PER MEMBER)
    # ------------------------------------------------------
    for member in members:
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
            },
        )

        report.binary_income = Decimal("0.00")
        report.binary_eligibility_income = Decimal("0.00")
        report.sponsor_income = Decimal("0.00")
        report.flashout_wallet_income = Decimal("0.00")
        report.sponsor_processed = False

        # -------------------------------
        # TODAY joins (DATE BASED ONLY)
        # -------------------------------
        left_today = Member.objects.filter(
            placement_id=member.id,
            side='left',             # ✅ Changed from 'position' to 'side'
            joined_date=run_date,    # ✅ Corrected field name
            is_active=True
        ).count()

        right_today = Member.objects.filter(
            placement_id=member.id,
            side='right',            # ✅ Changed from 'position' to 'side'
            joined_date=run_date,    # ✅ Corrected field name
            is_active=True
        ).count()

        res = calculate_member_binary_income_for_day(
            left_today,
            right_today,
            report.left_cf,
            report.right_cf,
            member.binary_eligible,
        )

        report.binary_income = Decimal(res["binary_income"])
        report.binary_eligibility_income = Decimal(res["eligibility_income"])
        report.flashout_wallet_income = Decimal(res.get("flashout_income", 0))
        report.left_cf = res["left_cf_after"]
        report.right_cf = res["right_cf_after"]
        report.total_income = (
            report.binary_income
            + report.binary_eligibility_income
            + report.flashout_wallet_income
            + report.sponsor_income
        )
        report.save(update_fields=[
            "binary_income",
            "binary_eligibility_income",
            "flashout_wallet_income",
            "left_cf",
            "right_cf",
            "total_income"
        ])

        if res["new_binary_eligible"] and not member.binary_eligible:
            member.binary_eligible = True
            member.save(update_fields=["binary_eligible"])
            print(f"✅ {member.member_id} is now binary eligible and credited ₹500")


    # ------------------------------------------------------
    # 2️⃣ Sponsor Income (FINAL – CLEAN VERSION)
    # ------------------------------------------------------
    for child in members:
        child_report = DailyIncomeReport.objects.get(
            member=child,
            date=run_date,
        )

        # child earned nothing today
        if (
            (child_report.binary_income or 0) == 0
            and (child_report.binary_eligibility_income or 0) == 0
        ):
            continue

        if child_report.sponsor_processed:
            continue

        sponsor = None

        # Rule 1: placement == sponsor → placement parent
        if child.placement_id == child.sponsor_id:
            if (
                child.placement
                and child.placement.parent
                and child.placement.parent.auto_id != ROOT_ID
            ):
                sponsor = child.placement.parent
        else:
            # Rule 2: placement != sponsor → sponsor
            if child.sponsor and child.sponsor.auto_id != ROOT_ID:
                sponsor = child.sponsor

        # ❌ Dummy never earns
        if not sponsor or sponsor.auto_id == ROOT_ID:
            child_report.sponsor_processed = True
            child_report.save(update_fields=["sponsor_processed"])
            continue

        # Rule 3: sponsor must have 1:1
        if not (sponsor.left_child() and sponsor.right_child()):
            child_report.sponsor_processed = True
            child_report.save(update_fields=["sponsor_processed"])
            continue

        sponsor_amount = Decimal(
            (child_report.binary_income or 0)
            + (child_report.binary_eligibility_income or 0)
        )

        if sponsor_amount > 0:
            sponsor_report, _ = DailyIncomeReport.objects.get_or_create(
                member=sponsor,
                date=run_date,
                defaults={
                    "binary_income": Decimal("0"),
                    "binary_eligibility_income": Decimal("0"),
                    "sponsor_income": Decimal("0"),
                    "flashout_wallet_income": Decimal("0"),
                    "total_income": Decimal("0"),
                },
            )

            sponsor_report.sponsor_income = Decimal(sponsor_report.sponsor_income or 0) + sponsor_amount
            sponsor_report.total_income = (
                sponsor_report.binary_income
                + sponsor_report.binary_eligibility_income
                + sponsor_report.flashout_wallet_income
                + sponsor_report.sponsor_income
            )
            sponsor_report.save(update_fields=["sponsor_income", "total_income"])

            sponsor.sponsor_income = Decimal(sponsor.sponsor_income or 0) + sponsor_amount
            sponsor.main_wallet = Decimal(sponsor.main_wallet or 0) + sponsor_amount
            sponsor.save(update_fields=["sponsor_income", "main_wallet"])

            print(f"✅ Sponsor income {sponsor_amount} credited to {sponsor.member_id}")

        child_report.sponsor_processed = True
        child_report.save(update_fields=["sponsor_processed"])


    # ------------------------------------------------------
    # 3️⃣ Final Total
    # ------------------------------------------------------
    for report in DailyIncomeReport.objects.filter(date=run_date):
        report.total_income = (
            report.binary_income
            + report.binary_eligibility_income
            + report.sponsor_income
            + report.flashout_wallet_income
        )
        report.save(update_fields=["total_income"])
# ----------------------------------------------------------
# Django Command - untouched
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

