# herbalapp/mlm_engine_binary_runner.py
from decimal import Decimal
from django.db import transaction
from herbalapp.models import DailyIncomeReport
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day


@transaction.atomic
def run_binary_engine(member, run_date):
    report, _ = DailyIncomeReport.objects.get_or_create(
        member=member,
        date=run_date,
        defaults={
            "binary_eligibility_income": Decimal("0"),
            "binary_income": Decimal("0"),
            "flashout_units": 0,
            "flashout_wallet_income": Decimal("0"),
            "sponsor_income": Decimal("0"),
            "total_income": Decimal("0"),
            "left_cf": 0,
            "right_cf": 0,
            "sponsor_processed": False,
        }
    )

    # -------------------------------
    # TODAY joins (do NOT subtract CF)
    # -------------------------------
    left_today = 1 if member.left_child() else 0
    right_today = 1 if member.right_child() else 0

    # -------------------------------
    # calculate binary income using rules
    # -------------------------------
    res = calculate_member_binary_income_for_day(
        left_today,
        right_today,
        report.left_cf,
        report.right_cf,
        member.binary_eligible
    )

    # -------------------------------
    # update report fields
    # -------------------------------
    report.binary_income = Decimal(res["binary_income"])
    report.binary_eligibility_income = Decimal(res["eligibility_income"])
    report.flashout_units = res["flashout_units"]
    report.flashout_wallet_income = Decimal(res.get("flashout_income", 0))
    report.left_cf = res["left_cf_after"]
    report.right_cf = res["right_cf_after"]
    report.total_income = (
        report.binary_income +
        report.binary_eligibility_income +
        report.flashout_wallet_income +
        report.sponsor_income
    )

    report.save()

    # -------------------------------
    # update member eligibility flag (lifetime)
    # -------------------------------
    if res["new_binary_eligible"] and not member.binary_eligible:
        member.binary_eligible = True
        member.save(update_fields=["binary_eligible"])

