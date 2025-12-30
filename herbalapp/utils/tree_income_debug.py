# herbalapp/utils/tree_income_debug.py
# ----------------------------------------------------------
# ✅ Genealogy tree income debug printer
# ----------------------------------------------------------

from herbalapp.models import Member
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day
import datetime


def genealogy_tree_income_debug(root_member_id: str):
    """
    Print genealogy tree structure + engine-based income debug.
    """
    try:
        root = Member.objects.get(member_id=root_member_id)
    except Member.DoesNotExist:
        return f"❌ Member {root_member_id} not found"

    header = f"Genealogy Tree for {root.member_id} - {root.name}\n"
    header += "=============================================\n"

    # Engine-based income calculation (using today's date)
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

    income_str = (
        f"\nIncome Debug (Engine Rules):\n"
        f" - Eligibility bonus: ₹{debug_result['eligibility_income']}\n"
        f" - Binary income: ₹{debug_result['binary_income']} (pairs paid={debug_result['binary_pairs']})\n"
        f" - Flashout income (repurchase wallet): ₹{debug_result['flashout_income']} (units={debug_result['flashout_units']})\n"
        f" - Sponsor income credited: ₹{debug_result['child_total_for_sponsor']}\n"
        f" - Carry forward left: {debug_result['left_cf']}\n"
        f" - Carry forward right: {debug_result['right_cf']}\n"
        f" - Binary eligible: {debug_result['binary_eligible']}\n"
    )

    return header + income_str

