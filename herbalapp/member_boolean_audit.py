# herbalapp/member_boolean_audit.py

from django.utils import timezone
from django.db.models import Sum
from herbalapp.models import Member, IncomeRecord, SponsorIncome

def audit_member_boolean(member_member_id: str, run_date=None):
    run_date = run_date or timezone.now().date()
    result = {}

    try:
        m = Member.objects.get(member_id=member_member_id)
    except Member.DoesNotExist:
        return {"member_exists": False}

    # Binary eligibility
    result["binary_eligible"] = bool(m.binary_eligible)

    # IncomeRecord today
    rec_qs = IncomeRecord.objects.filter(member=m, created_at__date=run_date)
    result["has_income_record_today"] = rec_qs.exists()
    result["credited_today"] = rec_qs.exists() and (rec_qs.first().amount or 0) > 0

    # Sponsor routing rules
    placement_id = getattr(m.placement, "member_id", None) if hasattr(m, "placement") and m.placement else None
    sponsor_id = getattr(m.sponsor, "member_id", None) if hasattr(m, "sponsor") and m.sponsor else None
    parent_id = getattr(m.parent, "member_id", None) if hasattr(m, "parent") and m.parent else None

    if placement_id and sponsor_id:
        if placement_id == sponsor_id:
            result["routing_rule1"] = True
            result["routing_rule2"] = False
            routed_target = parent_id
        else:
            result["routing_rule1"] = False
            result["routing_rule2"] = True
            routed_target = sponsor_id
    else:
        result["routing_rule1"] = False
        result["routing_rule2"] = False
        routed_target = None

    # Rule 3: receiver has ≥1 pair
    receiver_has_pair = False
    if routed_target:
        try:
            receiver = Member.objects.get(member_id=routed_target)
            binary_credit_sum = IncomeRecord.objects.filter(member=receiver).aggregate(s=Sum("binary_income"))["s"] or 0
            receiver_has_pair = binary_credit_sum >= 500
        except Member.DoesNotExist:
            receiver_has_pair = False
    result["routing_rule3"] = receiver_has_pair

    # SponsorIncome record today
    si_qs = SponsorIncome.objects.filter(date=run_date, child=m)
    result["sponsor_income_today"] = si_qs.exists()

    # Pairs today
    pairs_today = int((rec_qs.first().binary_income or 0) / 500) if rec_qs.exists() else 0
    result["pairs_today_valid"] = pairs_today > 0
    result["pairs_within_limit"] = pairs_today <= 5
    result["flashout_unit"] = pairs_today > 5
    result["washout_exists"] = pairs_today > (5 + 9 * 5)

    # Consistency check
    sponsor_sum = si_qs.aggregate(s=Sum("amount"))["s"] or 0
    mirror_sum_today = IncomeRecord.objects.filter(member__member_id=routed_target, created_at__date=run_date).aggregate(s=Sum("sponsor_income"))["s"] or 0
    result["sponsor_match"] = sponsor_sum == mirror_sum_today

    return result

