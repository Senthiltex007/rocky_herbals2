# herbalapp/mlm_engine_binary_runner.py

from decimal import Decimal
from django.db import transaction
from herbalapp.models import DailyIncomeReport
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day


@transaction.atomic
def run_binary_engine(member, run_date):
    report, _ = DailyIncomeReport.objects.get_or_create(
        member=member,
        date=run_date
    )

    # reset daily values
    report.binary_income = Decimal("0.00")
    report.binary_eligibility_income = Decimal("0.00")
    report.flashout_units = 0
    report.total_income = Decimal("0.00")

    left_today = (1 if member.left_child() else 0) - report.left_cf
    right_today = (1 if member.right_child() else 0) - report.right_cf

    res = calculate_member_binary_income_for_day(
        left_today,
        right_today,
        report.left_cf,
        report.right_cf,
        member.binary_eligible
    )

    # ✅ STRICT: binary only if REAL 1:1 pair
    if res.get("binary_pairs_paid", 0) > 0:
        report.binary_income = Decimal(res["binary_income"])
    else:
        report.binary_income = Decimal("0.00")

    # eligibility bonus
    report.binary_eligibility_income = Decimal(res["eligibility_income"])

    # carry forward
    report.left_cf = res["left_cf_after"]
    report.right_cf = res["right_cf_after"]

    # total (NO sponsor here)
    report.total_income = (
        report.binary_income +
        report.binary_eligibility_income
    )

    report.save()

    # update member eligibility flag
    if res["new_binary_eligible"] and not member.binary_eligible:
        member.binary_eligible = True
        member.save(update_fields=["binary_eligible"])

