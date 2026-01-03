# herbalapp/engine/run.py

from django.db import transaction
from herbalapp.utils.tree import count_subtree
from herbalapp.engine.eligibility import became_binary_eligible_today

def credit_eligibility_bonus(member, amount, run_date):
    # TODO: insert/update DailyIncomeReport row
    print(f"Eligibility bonus {amount} credited to {member.auto_id} on {run_date}")

def credit_binary_income(member, pairs, run_date):
    # TODO: implement binary income logic with carry-forward/flashout
    print(f"Binary income {pairs*500} credited to {member.auto_id} on {run_date}")

@transaction.atomic
def process_member_daily(member, run_date):
    left_total = count_subtree(member, "left")
    right_total = count_subtree(member, "right")

    if became_binary_eligible_today(member, left_total, right_total):
        credit_eligibility_bonus(member, amount=500, run_date=run_date)
        member.binary_eligible_since = run_date
        member.save(update_fields=["binary_eligible_since"])

    if member.binary_eligible_since:
        pairs = min(left_total, right_total)
        credit_binary_income(member, pairs, run_date)

