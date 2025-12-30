# herbalapp/run_daily_engine.py
# Thin wrapper → redirects to final engine

from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day
from herbalapp.models import Member
import datetime

def run_daily_engine(run_date=None):
    """
    Wrapper for backward compatibility.
    Loops through all members and calls the final binary engine.
    """
    if run_date is None:
        run_date = datetime.date.today()

    results = []
    for member in Member.objects.all():
        results.append(
            calculate_member_binary_income_for_day(
                left_joins_today=0,
                right_joins_today=0,
                left_cf_before=0,
                right_cf_before=0,
                binary_eligible=member.binary_eligible,
                member=member,
                run_date=run_date
            )
        )
    return results

