# herbalapp/utils/tree_utils.py
# ----------------------------------------------------------
# ✅ Extra genealogy tree utilities
# ----------------------------------------------------------

from herbalapp.models import Member
from herbalapp.utils.tree import ascend_to_root, count_subtree, print_tree
from herbalapp.utils.tree_json import build_tree_json
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day
import datetime


def get_root_info(member: Member):
    """
    Return root ancestor info for a given member.
    """
    root = ascend_to_root(member)
    return {
        "root_member_id": root.member_id,
        "root_name": root.name,
    }


def get_subtree_counts(member: Member):
    """
    Return left/right subtree counts for a given member.
    """
    return {
        "left_count": count_subtree(member, "left"),
        "right_count": count_subtree(member, "right"),
    }


def get_income_snapshot(member: Member):
    """
    Run binary income engine for member and return snapshot.
    """
    run_date = datetime.date.today()
    result = calculate_member_binary_income_for_day(
        left_joins_today=0,
        right_joins_today=0,
        left_cf_before=0,
        right_cf_before=0,
        binary_eligible=member.binary_eligible,
        member=member,
        run_date=run_date
    )
    return {
        "eligibility_bonus": result["eligibility_income"],
        "binary_income": result["binary_income"],
        "flashout_income": result["flashout_income"],
        "sponsor_income_credit": result["child_total_for_sponsor"],
        "left_cf": result["left_cf"],
        "right_cf": result["right_cf"],
        "binary_eligible": result["binary_eligible"],
        "flash_units_used": result["flashout_units"],
    }


def get_tree_json(root_member_id: str):
    """
    Build JSON for genealogy tree starting from root_member_id.
    """
    try:
        root = Member.objects.get(member_id=root_member_id)
    except Member.DoesNotExist:
        return {"error": f"Member {root_member_id} not found"}
    return build_tree_json(root)


def debug_tree(root_member_id: str):
    """
    Full debug: tree text + counts + income snapshot.
    """
    try:
        root = Member.objects.get(member_id=root_member_id)
    except Member.DoesNotExist:
        return f"❌ Member {root_member_id} not found"

    header = f"Genealogy Tree Debug for {root.member_id} - {root.name}\n"
    header += "=============================================\n"
    tree_str = print_tree(root, prefix="", is_left=True)

    counts = get_subtree_counts(root)
    income = get_income_snapshot(root)

    counts_str = (
        f"\nSubtree Counts:\n"
        f" - Left subtree count: {counts['left_count']}\n"
        f" - Right subtree count: {counts['right_count']}\n"
    )

    income_str = (
        f"\nIncome Snapshot:\n"
        f" - Eligibility bonus: ₹{income['eligibility_bonus']}\n"
        f" - Binary income: ₹{income['binary_income']}\n"
        f" - Flashout income: ₹{income['flashout_income']}\n"
        f" - Sponsor credited: ₹{income['sponsor_income_credit']}\n"
        f" - Carry forward left: {income['left_cf']}\n"
        f" - Carry forward right: {income['right_cf']}\n"
        f" - Binary eligible: {income['binary_eligible']}\n"
        f" - Flash units used: {income['flash_units_used']}\n"
    )

    return header + tree_str + counts_str + income_str

