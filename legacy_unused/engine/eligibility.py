# herbalapp/engine/eligibility.py

def is_binary_eligible(left_total, right_total):
    """
    Eligibility rule:
    - One leg >= 1
    - Other leg >= 2
    => 1:2 or 2:1 structure
    """
    return (min(left_total, right_total) >= 1) and (max(left_total, right_total) >= 2)

def became_binary_eligible_today(member, left_total, right_total):
    """
    Detect first-time eligibility transition.
    """
    already = member.binary_eligible_since is not None
    now_eligible = is_binary_eligible(left_total, right_total)
    return (not already) and now_eligible

