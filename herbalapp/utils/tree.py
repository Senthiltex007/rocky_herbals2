# herbalapp/utils/tree.py
# ----------------------------------------------------------
# ✅ Tree utilities with income debug
# ----------------------------------------------------------

from herbalapp.models import Member
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day
import datetime


def debug_tree(root: Member):
    """
    Run binary income engine for root member and return debug snapshot.
    """
    run_date = datetime.date.today()
    debug_result = calculate_member_binary_income_for_day(
        left_joins_today=0,
        right_joins_today=0,
        left_cf_before=0,
        right_cf_before=0,
        binary_eligible=root.binary_eligible,
        member=root,
        run_date=run_date
    )
    return {
        "eligibility_bonus": debug_result["eligibility_income"],
        "binary_income": debug_result["binary_income"],
        "flashout_income": debug_result["flashout_income"],
        "sponsor_income_credit": debug_result["child_total_for_sponsor"],
        "left_cf": debug_result["left_cf"],
        "right_cf": debug_result["right_cf"],
        "binary_eligible": debug_result["binary_eligible"],
        "flash_units_used": debug_result["flashout_units"],
    }

