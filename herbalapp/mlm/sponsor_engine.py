# herbalapp/mlm/sponsor_engine.py

from decimal import Decimal
from django.db import transaction
from herbalapp.models import Member, DailyIncomeReport

ROOT_ID = "rocky004"


def is_sponsor_binary_eligible(member: Member) -> bool:
    return bool(member.left_child() and member.right_child())


def get_sponsor_receiver(child: Member):
    """
    Decide who should receive sponsor income for this child
    """
    if not child.sponsor or child.sponsor.auto_id == ROOT_ID:
        return None

    # self-sponsor case
    if child.placement_id == child.sponsor_id:
        parent = child.placement.parent if child.placement else None
        if parent and parent.auto_id != ROOT_ID:
            return parent
        return None

    return child.sponsor


def calculate_sponsor_amount(child_report) -> Decimal:
    """
    Sponsor income = child binary + eligibility
    Flashout NOT included
    """
    return (
        (child_report.binary_income or Decimal("0")) +
        (child_report.binary_eligibility_income or Decimal("0"))
    )


# ----------------------------------------------------------
# RUN SPONSOR ENGINE
# ----------------------------------------------------------
@transaction.atomic
def run_sponsor_engine(member: Member, run_date):
    """
    Process sponsor income for a single member's children.
    This will credit sponsor_income and update total_income.
    """
    # Get all direct children of this member
    children = Member.objects.filter(sponsor=member)

    for child in children:
        # Get child's daily report
        child_report, _ = DailyIncomeReport.objects.get_or_create(
            member=child,
            date=run_date,
            defaults={
                "binary_income": 0,
                "binary_eligibility_income": 0,
                "sponsor_income": 0,
                "flashout_wallet_income": 0,
                "total_income": 0,
            }
        )

        # Skip if already processed
        if getattr(child_report, "sponsor_processed", False):
            continue

        # Determine sponsor
        sponsor = get_sponsor_receiver(child)
        if not sponsor:
            child_report.sponsor_processed = True
            child_report.save(update_fields=["sponsor_processed"])
            continue

        # Check if sponsor eligible
        if not is_sponsor_binary_eligible(sponsor):
            child_report.sponsor_processed = True
            child_report.save(update_fields=["sponsor_processed"])
            continue

        # Calculate sponsor amount
        sponsor_amount = calculate_sponsor_amount(child_report)
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
            sponsor_report.total_income += sponsor_amount
            sponsor_report.save(update_fields=["sponsor_income", "total_income"])

        # Mark child processed
        child_report.sponsor_processed = True
        child_report.save(update_fields=["sponsor_processed"])

