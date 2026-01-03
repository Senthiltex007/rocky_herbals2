# herbalapp/sponsor_engine.py

from herbalapp.models import Member, SponsorIncome, IncomeRecord
from decimal import Decimal
from django.db import models

def has_completed_one_to_one(member):
    """
    Lifetime 1:1 completion:
    - Either model has boolean flag, or lifetime_pairs > 0, or any past IncomeRecord shows binary_pairs >= 1
    """
    if hasattr(member, "has_completed_first_pair") and member.has_completed_first_pair:
        return True
    if hasattr(member, "lifetime_pairs") and (member.lifetime_pairs or 0) > 0:
        return True
    # Fallback check
    rec = IncomeRecord.objects.filter(member=member, binary_pairs__gte=1).exists()
    return rec

def resolve_sponsor_receiver(child):
    """
    Rule 1: if placement_id == sponsor_id → sponsor income goes to placement's parent
    Rule 2: else → sponsor income goes to sponsor_id
    """
    placement = child.placement
    sponsor = child.sponsor
    if not placement or not sponsor:
        return None
    if placement.id == sponsor.id:
        # parent of placement (if exists), else placement itself
        return getattr(placement, "placement", None) or placement
    return sponsor

def process_sponsor_income(child_member, run_date, child_became_eligible_today=False):
    """
    Rule 3: Receiver must have lifetime 1:1 pair completed.
    Amount to credit = child's eligibility (₹500 if today unlocked) + child's sponsor income today.
    Prevent duplicates per (receiver, child, date).
    """
    receiver = resolve_sponsor_receiver(child_member)
    if not receiver:
        return None

    # Rule 3 check
    if not has_completed_one_to_one(receiver):
        return None

    # Amount = child eligibility bonus + child sponsor income
    child_eligibility = 500 if child_became_eligible_today else 0

    child_sponsor_today = IncomeRecord.objects.filter(
        member=child_member,
        created_at__date=run_date,
        type="sponsor_income"
    ).aggregate(total=models.Sum("amount"))["total"] or 0

    amount = child_eligibility + int(child_sponsor_today)
    if amount <= 0:
        return None

    # Prevent duplicate
    existing = SponsorIncome.objects.filter(sponsor=receiver, child=child_member, date=run_date).first()
    if existing:
        return existing.amount

    # Create credit
    si = SponsorIncome.objects.create(
        sponsor=receiver,
        child=child_member,
        amount=amount,
        date=run_date
    )

    # Update receiver's IncomeRecord for the day
    rec = IncomeRecord.objects.filter(member=receiver, created_at__date=run_date).last()
    if rec:
        rec.sponsor_income = (rec.sponsor_income or 0) + amount
        rec.total_income = (rec.total_income or 0) + amount
        rec.save()

    # ✅ Update DailyIncomeReport too
    from herbalapp.models import DailyIncomeReport
    r, created = DailyIncomeReport.objects.get_or_create(
        member=receiver,
        date=run_date,
        defaults={
            "eligibility_income": Decimal("0.00"),
            "binary_income": Decimal("0.00"),
            "sponsor_income": Decimal(amount),
            "wallet_income": Decimal("0.00"),
            "salary_income": Decimal("0.00"),
            "total_income": Decimal(amount),
        }
    )
    if not created:
        r.sponsor_income += Decimal(amount)
        r.total_income = (
            r.eligibility_income +
            r.binary_income +
            r.sponsor_income +
            r.wallet_income +
            r.salary_income
        )
        r.save()

    return si.amount

