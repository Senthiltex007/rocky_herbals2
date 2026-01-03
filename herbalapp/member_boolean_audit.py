# herbalapp/member_boolean_audit.py

from django.utils import timezone
from django.db.models import Sum
from herbalapp.models import Member, IncomeRecord, SponsorIncome, DailyIncomeReport

def has_completed_one_to_one(member):
    """
    Lifetime 1:1 completion:
    - Either model has boolean flag,
    - Or lifetime_pairs > 0,
    - Or any past IncomeRecord shows binary_pairs >= 1
    """
    if getattr(member, "has_completed_first_pair", False):
        return True
    if getattr(member, "lifetime_pairs", 0) > 0:
        return True
    return IncomeRecord.objects.filter(member=member, binary_pairs__gte=1).exists()

def audit_member_boolean(member_auto_id: str, run_date=None):
    run_date = run_date or timezone.now().date()
    result = {}

    try:
        m = Member.objects.get(auto_id=member_auto_id)
    except Member.DoesNotExist:
        return {"member_exists": False}

    # Binary eligibility
    result["binary_eligible"] = bool(m.binary_eligible)

    # IncomeRecord today
    rec_qs = IncomeRecord.objects.filter(member=m, created_at__date=run_date)
    result["has_income_record_today"] = rec_qs.exists()
    result["credited_today"] = rec_qs.exists() and (rec_qs.first().amount or 0) > 0

    # Sponsor routing rules
    placement_id = getattr(m.placement, "auto_id", None) if hasattr(m, "placement") and m.placement else None
    sponsor_id = getattr(m.sponsor, "auto_id", None) if hasattr(m, "sponsor") and m.sponsor else None
    parent_id = getattr(m.parent, "auto_id", None) if hasattr(m, "parent") and m.parent else None

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

    from datetime import date
    from herbalapp.member_boolean_audit import audit_member_boolean
    print(audit_member_boolean("rocky005", run_date=date(2026,1,3)))

    # Rule 3: receiver has lifetime eligibility
    receiver_has_pair = False
    if routed_target:
        try:
            receiver = Member.objects.get(auto_id=routed_target)
            receiver_has_pair = has_completed_one_to_one(receiver)
            result["receiver_has_first_pair"] = receiver_has_pair
        except Member.DoesNotExist:
            receiver_has_pair = False
            result["receiver_has_first_pair"] = False
    result["routing_rule3"] = receiver_has_pair

    # Eligibility bonus check
    elig_today = IncomeRecord.objects.filter(
        member=m,
        created_at__date=run_date,
        type="eligibility_bonus"
    ).exists()
    result["eligibility_bonus_today"] = elig_today

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
    mirror_sum_today = IncomeRecord.objects.filter(
        member__auto_id=routed_target,
        created_at__date=run_date
    ).aggregate(s=Sum("sponsor_income"))["s"] or 0
    result["sponsor_match"] = sponsor_sum == mirror_sum_today

    # DailyIncomeReport consistency
    dr = DailyIncomeReport.objects.filter(member__auto_id=routed_target, date=run_date).first()
    result["daily_report_sponsor_income"] = dr.sponsor_income if dr else 0
    result["daily_report_match"] = sponsor_sum == (dr.sponsor_income if dr else 0)

    return result

