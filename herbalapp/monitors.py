# herbalapp/monitors.py

from django.utils import timezone
from decimal import Decimal
from herbalapp.models import (
    AuditDailyReport,
    Member,
    IncomeRecord,
    DailyIncomeReport
)

def monitor_all_in_one(run_date=None):
    if run_date is None:
        run_date = timezone.now().date()

    # -------------------------------
    # Summary counters
    # -------------------------------
    processed_members = Member.objects.count()

    binary_qs = IncomeRecord.objects.filter(date=run_date, type="binary_engine")
    sponsor_qs = IncomeRecord.objects.filter(date=run_date, type="sponsor_income")
    eligibility_qs = IncomeRecord.objects.filter(date=run_date, type="eligibility_bonus")

    total_binary_income = sum(r.binary_income or Decimal("0.00") for r in binary_qs)
    total_wallet_income = sum(r.wallet_income or Decimal("0.00") for r in binary_qs)

    # ✅ Eligibility bonus from eligibility_bonus records
    total_eligibility_income = sum(r.amount or Decimal("0.00") for r in eligibility_qs)

    total_sponsor_income = sum(r.amount or Decimal("0.00") for r in sponsor_qs)
    sponsor_count = sponsor_qs.count()

    flashout_units = sum(r.flashout_units or 0 for r in binary_qs)
    washout_pairs = sum(r.washed_pairs or 0 for r in binary_qs)

    income_total = (
        total_binary_income +
        total_eligibility_income +
        total_wallet_income +
        total_sponsor_income
    )

    # -------------------------------
    # Save / Update AuditDailyReport
    # -------------------------------
    AuditDailyReport.objects.update_or_create(
        date=run_date,
        defaults={
            "processed_members": processed_members,
            "total_binary_income": total_binary_income,
            "total_sponsor_income": total_sponsor_income,
            "flashout_units": flashout_units,
            "washout_pairs": washout_pairs,
            "total_eligibility_income": total_eligibility_income,
            "total_wallet_income": total_wallet_income,
            "income_total": income_total,   # ✅ added
        }
    )

    # -------------------------------
    # Print audit
    # -------------------------------
    print(f"\n=== All-in-One Monitor for {run_date} ===")
    print(f"Processed Members           : {processed_members}")
    print(f"Eligibility Bonus           : {total_eligibility_income}")
    print(f"Binary Income               : {total_binary_income}")
    print(f"Sponsor Income              : {total_sponsor_income} (Records={sponsor_count})")
    print(f"Flashout Units              : {flashout_units}")
    print(f"Repurchase Wallet Bonus     : {total_wallet_income}")
    print(f"Washout Pairs               : {washout_pairs}")
    print(f"Total Income (All Streams)  : {income_total}")

    # -------------------------------
    # Sponsor Income Records
    # -------------------------------
    print("\n--- Sponsor Income Records ---")
    for rec in sponsor_qs.select_related("member"):
        print(f"Sponsor {rec.member.auto_id} credited ₹{rec.amount}")

    # -------------------------------
    # IncomeRecord Entries
    # -------------------------------
    print("\n--- IncomeRecord Entries ---")
    for rec in IncomeRecord.objects.filter(date=run_date).select_related("member"):
        print(
            f"Member {rec.member.auto_id} | "
            f"Eligibility={rec.eligibility_income if rec.type=='binary_engine' else (rec.amount if rec.type=='eligibility_bonus' else Decimal('0.00'))} | "
            f"Binary={rec.binary_income} | "
            f"Sponsor={rec.amount if rec.type=='sponsor_income' else Decimal('0.00')} | "  # ✅ simplified
            f"Wallet={rec.wallet_income} | "
            f"Salary={rec.salary_income} | "
            f"Total={rec.total_income}"
        )

    # -------------------------------
    # DailyIncomeReport summary
    # -------------------------------
    print("\n--- DailyIncomeReport Summary ---")
    for r in DailyIncomeReport.objects.filter(date=run_date).select_related("member"):
        print(
            f"DailyReport {r.member.auto_id} | "
            f"Eligibility={r.eligibility_income} | "
            f"Binary={r.binary_income} | "
            f"Sponsor={r.sponsor_income} | "
            f"Wallet={r.wallet_income} | "
            f"Salary={r.salary_income} | "
            f"Total={r.total_income}"
        )

    return {
        "date": run_date,
        "processed_members": processed_members,
        "total_eligibility_income": total_eligibility_income,
        "total_binary_income": total_binary_income,
        "total_sponsor_income": total_sponsor_income,
        "sponsor_records_count": sponsor_count,
        "flashout_units": flashout_units,
        "total_wallet_income": total_wallet_income,
        "washout_pairs": washout_pairs,
        "income_total": income_total,
    }

