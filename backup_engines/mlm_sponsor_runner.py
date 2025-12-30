# herbalapp/mlm_sponsor_runner.py
# Thin wrapper → redirects to final engine

from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day

def run_daily_binary_and_sponsor(member, run_date):
    """
    Wrapper for backward compatibility.
    Calls the final binary engine.
    """
    return calculate_member_binary_income_for_day(
        left_joins_today=0,
        right_joins_today=0,
        left_cf_before=0,
        right_cf_before=0,
        binary_eligible=member.binary_eligible,
        member=member,
        run_date=run_date
    )

