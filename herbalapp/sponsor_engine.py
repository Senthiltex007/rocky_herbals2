# herbalapp/sponsor_engine.py

from herbalapp.models import Member, SponsorIncome, IncomeRecord

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

def process_sponsor_income(child_member, run_date, child_total_for_sponsor, child_became_eligible_today=False):
    """
    Rule 3: Receiver must have lifetime 1:1 pair completed.
    Amount to credit = child's eligibility (₹500 if today unlocked) + child's binary income today.
    Prevent duplicates per (receiver, child, date).
    """
    receiver = resolve_sponsor_receiver(child_member)
    if not receiver:
        return None

    # Rule 3 check
    if not has_completed_one_to_one(receiver):
        return None

    # Amount
    amount = (500 if child_became_eligible_today else 0) + int(child_total_for_sponsor or 0)
    if amount <= 0:
        return None

    # Prevent duplicate
    existing = SponsorIncome.objects.filter(sponsor=receiver, child=child_member, date=run_date).first()
    if existing:
        # already credited
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

    return si.amount

