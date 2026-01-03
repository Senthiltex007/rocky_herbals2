# herbalapp/engines/sponsor_logic.py

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport, SponsorIncome

ELIGIBILITY_BONUS = Decimal("500.00")
BINARY_PER_PAIR = Decimal("500.00")

def has_lifetime_one_one(member: Member) -> bool:
    """
    Return True if member has at least one 1:1 pair lifetime.
    You can compute from stored counters or historical snapshots.
    Assumes member.left_total_pairs and member.right_total_pairs or equivalent.
    """
    # If you store cumulative pairs:
    try:
        return (member.left_total_pairs or 0) >= 1 and (member.right_total_pairs or 0) >= 1
    except AttributeError:
        # Fallback: derive from DailyIncomeReport totals if needed
        total_pairs = DailyIncomeReport.objects.filter(member=member).aggregate_pairs()
        # Implement aggregate_pairs() or compute from binary_income / BINARY_PER_PAIR
        return (total_pairs.get("left_pairs", 0) >= 1 and total_pairs.get("right_pairs", 0) >= 1)


def resolve_sponsor_receiver(placement_member: Member, sponsor_member: Member) -> Member:
    """
    Rule 1: If placement == sponsor → receiver is placement.parent
    Rule 2: Else → receiver is sponsor
    """
    if placement_member.id == sponsor_member.id:
        # parent of placement gets sponsor income
        return placement_member.sponsor  # assuming 'sponsor' is parent in tree
    return sponsor_member


@transaction.atomic
def credit_sponsor_income_for_join(child: Member, placement_member: Member, sponsor_member: Member, run_date=None):
    """
    Called when a child joins. Applies sponsor rules and credits sponsor income if eligible.
    Amount = child eligibility bonus (if today) + child's sponsor income for that day.
    """
    if run_date is None:
        run_date = timezone.now().date()

    receiver = resolve_sponsor_receiver(placement_member, sponsor_member)
    if receiver is None:
        return {"credited": False, "reason": "No receiver (root without parent)"}

    # Eligibility check for sponsor receiver
    if not has_lifetime_one_one(receiver):
        return {"credited": False, "reason": "Receiver not lifetime 1:1 eligible"}

    # Compute child’s amounts for the day
    child_report = DailyIncomeReport.objects.filter(member=child, date=run_date).first()
    child_elig = child_report.eligibility_income if child_report else Decimal("0.00")
    child_sponsor_today = child_report.sponsor_income if child_report else Decimal("0.00")

    # Amount to credit
    amount = (child_elig or Decimal("0.00")) + (child_sponsor_today or Decimal("0.00"))
    if amount <= 0:
        # If eligibility already paid earlier or no sponsor income today, still allow ₹500 if today is unlock day
        # You can pass a flag from your join handler to indicate unlock day
        pass

    # Create SponsorIncome record
    SponsorIncome.objects.create(
        sponsor=receiver,
        child=child,
        amount=amount,
        date=run_date,
    )

    # Update DailyIncomeReport for receiver
    recv_report, _ = DailyIncomeReport.objects.get_or_create(member=receiver, date=run_date, defaults={
        "eligibility_income": Decimal("0.00"),
        "binary_income": Decimal("0.00"),
        "sponsor_income": Decimal("0.00"),
        "wallet_income": Decimal("0.00"),
        "salary_income": Decimal("0.00"),
        "total_income": Decimal("0.00"),
    })
    recv_report.sponsor_income = (recv_report.sponsor_income or Decimal("0.00")) + amount
    recv_report.total_income = (
        (recv_report.eligibility_income or Decimal("0.00")) +
        (recv_report.binary_income or Decimal("0.00")) +
        (recv_report.sponsor_income or Decimal("0.00")) +
        (recv_report.wallet_income or Decimal("0.00")) +
        (recv_report.salary_income or Decimal("0.00"))
    )
    recv_report.save()

    return {"credited": True, "receiver": receiver.auto_id, "amount": str(amount)}

