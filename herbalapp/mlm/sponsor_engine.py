# herbalapp/mlm/sponsor_engine.py

from decimal import Decimal
from django.db import transaction

from herbalapp.models import DailyIncomeReport, Member
from herbalapp.mlm.filters import get_valid_sponsor_children

ROOT_ID = "rocky001"


def can_receive_sponsor_income(member: Member, run_date) -> bool:
    """
    Rule-3: Sponsor must have DIRECT 1:1 (one direct left + one direct right) as of run_date.
    This is NOT binary_eligible (1:2/2:1).
    Lifetime: once reached, always eligible after that date.
    """
    if not member:
        return False

    left_exists = Member.objects.filter(
        parent=member,
        side="left",
        is_active=True,
        joined_date__lte=run_date
    ).exists()

    right_exists = Member.objects.filter(
        parent=member,
        side="right",
        is_active=True,
        joined_date__lte=run_date
    ).exists()

    return left_exists and right_exists


def get_sponsor_receiver(child: Member, run_date):
    """
    Rule-1: placement_id == sponsor_id -> placement gets sponsor income
    Rule-2: placement_id != sponsor_id -> sponsor gets sponsor income
    Root never receives sponsor income
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

    if not receiver:
        return None

    if receiver.auto_id == ROOT_ID:
        return None

    if not can_receive_sponsor_income(receiver, run_date):
        return None

    return receiver


def run_sponsor_income_safe(run_date):
    """
    ✅ SAFE SPONSOR INCOME ENGINE (SINGLE SOURCE)

    RULES:
    1️⃣ Child must earn (binary_income > 0 OR binary_eligibility_income > 0) TODAY
    2️⃣ Receiver determined by placement_id vs sponsor_id
    3️⃣ Receiver must satisfy DIRECT 1:1 eligibility (as of run_date)
    4️⃣ ROOT never gets sponsor income
    5️⃣ sponsor_today_processed = HARD LOCK (no duplicates)
    6️⃣ Sponsor amount = child (binary + eligibility) only (NO flashout)
    """
    print(f"🔄 Running Sponsor Engine for {run_date}")

    children = get_valid_sponsor_children(run_date)

    for child in children:
        if child.auto_id == ROOT_ID:
            continue

        child_report = DailyIncomeReport.objects.filter(member=child, date=run_date).first()
        if not child_report:
            continue

        receiver = get_sponsor_receiver(child, run_date)
        if not receiver:
            continue

        sponsor_amount = child_report.binary_income + child_report.binary_eligibility_income
        if sponsor_amount <= 0:
            continue

        # ✅ DB-level lock (duplicate safe)
        updated = DailyIncomeReport.objects.filter(
            member=child,
            date=run_date,
            sponsor_today_processed=False
        ).update(sponsor_today_processed=True)

        if updated == 0:
            continue

        # ✅ atomic per credit
        with transaction.atomic():
            receiver_report, _ = DailyIncomeReport.objects.get_or_create(
                member=receiver,
                date=run_date,
                defaults={
                    "binary_income": Decimal("0.00"),
                    "binary_eligibility_income": Decimal("0.00"),
                    "eligibility_income": Decimal("0.00"),
                    "sponsor_income": Decimal("0.00"),
                    "flashout_wallet_income": Decimal("0.00"),
                    "total_income": Decimal("0.00"),
                    "left_cf": 0,
                    "right_cf": 0,
                    "earned_fresh_binary_today": False,
                    "sponsor_today_processed": False,
                    "total_income_locked": False,
                    "binary_income_processed": False,
                }
            )

            receiver_report.sponsor_income += sponsor_amount
            receiver_report.total_income += sponsor_amount
            receiver_report.save(update_fields=["sponsor_income", "total_income"])

        print(f"✅ Sponsor income {sponsor_amount} credited to {receiver.auto_id} (child {child.auto_id})")

    print("✅ Sponsor Engine Completed Successfully")

