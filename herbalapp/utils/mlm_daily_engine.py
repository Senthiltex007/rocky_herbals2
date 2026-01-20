# ==========================================================
# herbalapp/utils/mlm_daily_engine_final.py
# ==========================================================
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

from herbalapp.models import Member, DailyIncomeReport

ROOT_ID = "rocky004"

PAIR_VALUE = Decimal("500")
ELIGIBILITY_BONUS = Decimal("500")
DAILY_BINARY_PAIR_LIMIT = 5
FLASHOUT_PAIR_UNIT = 5
FLASHOUT_UNIT_INCOME = Decimal("1000")
MAX_FLASHOUT_UNITS_PER_DAY = 9

# ==========================================================
# 1️⃣ Binary + Eligibility Engine
# ==========================================================
def run_binary_engine(member: Member, run_date):

    report, _ = DailyIncomeReport.objects.get_or_create(
        member=member,
        date=run_date,
        defaults={
            "binary_eligibility_income": Decimal("0"),
            "binary_income": Decimal("0"),
            "flashout_wallet_income": Decimal("0"),
            "sponsor_income": Decimal("0"),
            "total_income": Decimal("0"),
            "left_cf": 0,
            "right_cf": 0,
            "sponsor_processed": False,
        }
    )

    # =========================
    # TODAY joins
    # =========================
    left_today = 1 if member.left_child() else 0
    right_today = 1 if member.right_child() else 0

    L = left_today + report.left_cf
    R = right_today + report.right_cf

    new_binary_eligible = member.binary_eligible
    eligibility_income = Decimal("0")
    binary_income = Decimal("0")
    flashout_income = Decimal("0")

    # -------------------------
    # Eligibility: 2:1 or 1:2
    # -------------------------
    if not member.binary_eligible and ((L >= 2 and R >= 1) or (L >= 1 and R >= 2)):
        new_binary_eligible = True
        eligibility_income = ELIGIBILITY_BONUS

        # Deduct eligibility pair
        if L >= 2 and R >= 1:
            L -= 2
            R -= 1
        else:
            L -= 1
            R -= 2

        # Binary income max 4 pairs on eligibility day
        total_pairs = min(L, R)
        binary_pairs_paid = min(total_pairs, 4)
        binary_income = binary_pairs_paid * PAIR_VALUE
        L -= binary_pairs_paid
        R -= binary_pairs_paid

        # Flashout bonus
        pairs_remaining = total_pairs - binary_pairs_paid
        flashout_units = min(pairs_remaining // FLASHOUT_PAIR_UNIT, MAX_FLASHOUT_UNITS_PER_DAY)
        flashout_income = flashout_units * FLASHOUT_UNIT_INCOME
        flashout_pairs_used = flashout_units * FLASHOUT_PAIR_UNIT
        L -= flashout_pairs_used
        R -= flashout_pairs_used

    else:
        # Normal day after eligibility
        total_pairs = min(L, R)
        binary_pairs_paid = min(total_pairs, DAILY_BINARY_PAIR_LIMIT)
        binary_income = binary_pairs_paid * PAIR_VALUE
        L -= binary_pairs_paid
        R -= binary_pairs_paid

        # Flashout bonus
        pairs_remaining = total_pairs - binary_pairs_paid
        flashout_units = min(pairs_remaining // FLASHOUT_PAIR_UNIT, MAX_FLASHOUT_UNITS_PER_DAY)
        flashout_income = flashout_units * FLASHOUT_UNIT_INCOME
        flashout_pairs_used = flashout_units * FLASHOUT_PAIR_UNIT
        L -= flashout_pairs_used
        R -= flashout_pairs_used

    # =========================
    # Update report
    # =========================
    report.binary_eligibility_income = eligibility_income
    report.binary_income = binary_income
    report.flashout_wallet_income = flashout_income
    report.left_cf = L
    report.right_cf = R
    report.save(update_fields=[
        "binary_eligibility_income",
        "binary_income",
        "flashout_wallet_income",
        "left_cf",
        "right_cf",
    ])

    # Update member binary eligibility flag
    if new_binary_eligible and not member.binary_eligible:
        member.binary_eligible = True
        member.save(update_fields=["binary_eligible"])

# ==========================================================
# 2️⃣ Sponsor Engine
# ==========================================================
def get_sponsor_receiver(child: Member):
    if not child.sponsor:
        return None
    if child.sponsor.auto_id == ROOT_ID:
        return None

    # Rule 1: placement == sponsor → placement.parent
    if child.placement_id == child.sponsor_id:
        if child.placement and child.placement.parent:
            if child.placement.parent.auto_id != ROOT_ID:
                return child.placement.parent
        return None

    # Rule 2: placement != sponsor → sponsor directly
    return child.sponsor

def can_receive_sponsor_income(sponsor: Member):
    left = 1 if sponsor.left_child() else 0
    right = 1 if sponsor.right_child() else 0
    return left >= 1 and right >= 1

def run_sponsor_engine(child: Member, run_date):
    child_report = DailyIncomeReport.objects.get(member=child, date=run_date)
    if child_report.sponsor_processed:
        return

    sponsor = get_sponsor_receiver(child)
    if not sponsor:
        child_report.sponsor_processed = True
        child_report.save(update_fields=["sponsor_processed"])
        return

    sponsor_amount = (child_report.binary_eligibility_income or Decimal("0")) + \
                     (child_report.binary_income or Decimal("0"))

    if sponsor_amount > 0 and can_receive_sponsor_income(sponsor):
        sponsor_report, _ = DailyIncomeReport.objects.get_or_create(member=sponsor, date=run_date)
        sponsor_report.sponsor_income += sponsor_amount
        sponsor_report.total_income += sponsor_amount
        sponsor_report.save(update_fields=["sponsor_income", "total_income"])

    child_report.sponsor_processed = True
    child_report.save(update_fields=["sponsor_processed"])

# ==========================================================
# 3️⃣ Daily Engine Wrapper
# ==========================================================
@transaction.atomic
def run_daily_engine(run_date=None):
    if not run_date:
        run_date = timezone.localdate()

    members = Member.objects.filter(is_active=True).order_by("id")

    # 1️⃣ Binary + Eligibility
    for member in members:
        run_binary_engine(member, run_date)

    # 2️⃣ Sponsor Income
    for member in members:
        run_sponsor_engine(member, run_date)

    # 3️⃣ Recalculate total_income
    for report in DailyIncomeReport.objects.filter(date=run_date):
        report.total_income = (
            report.binary_eligibility_income +
            report.binary_income +
            report.flashout_wallet_income +
            report.sponsor_income
        )
        report.save(update_fields=["total_income"])

# ==========================================================
# 4️⃣ Auto-run signal on new member join
# ==========================================================
@receiver(post_save, sender=Member)
def auto_run_engine_on_new_member(sender, instance, created, **kwargs):
    if created and instance.auto_id != ROOT_ID:
        run_daily_engine()

