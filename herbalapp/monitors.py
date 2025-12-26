# herbalapp/monitors.py

from django.utils import timezone
from herbalapp.models import AuditDailyReport, Member
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day
import datetime


def monitor_daily_engine(run_date=None):
    if run_date is None:
        run_date = timezone.now().date()

    processed_members = 0
    total_binary_income = 0
    total_sponsor_income = 0
    flashout_units = 0
    washout_pairs = 0

    # Loop through all members and run engine
    for member in Member.objects.all().order_by("id"):
        result = calculate_member_binary_income_for_day(
            left_joins_today=0,
            right_joins_today=0,
            left_cf_before=0,
            right_cf_before=0,
            binary_eligible=member.binary_eligible,
            member=member,
            run_date=run_date
        )
        processed_members += 1
        total_binary_income += result["binary_income"]
        total_sponsor_income += result["child_total_for_sponsor"]
        flashout_units += result["flashout_units"]
        washout_pairs += result["washed_pairs"]

    summary = {
        "date": run_date,
        "processed_members": processed_members,
        "total_binary_income": total_binary_income,
        "total_sponsor_income": total_sponsor_income,
        "flashout_units": flashout_units,
        "washout_pairs": washout_pairs,
    }

    AuditDailyReport.objects.create(
        date=summary["date"],
        processed_members=summary["processed_members"],
        total_binary_income=summary["total_binary_income"],
        total_sponsor_income=summary["total_sponsor_income"],
        flashout_units=summary["flashout_units"],
        washout_pairs=summary["washout_pairs"],
    )

    return summary

