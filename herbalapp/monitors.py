# herbalapp/monitors.py

from django.utils import timezone
from herbalapp.models import AuditDailyReport, Member, SponsorIncome, IncomeRecord
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day

def monitor_all_in_one(run_date=None):
    if run_date is None:
        run_date = timezone.now().date()

    processed_members = 0
    total_binary_income = 0
    flashout_units = 0
    washout_pairs = 0
    total_eligibility_income = 0
    total_wallet_income = 0

    # --- Run engine for all members ---
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
        flashout_units += result["flashout_units"]
        washout_pairs += result["washed_pairs"]
        total_eligibility_income += result["eligibility_income"]
        total_wallet_income += result["repurchase_wallet_bonus"]

    # --- SponsorIncome summary ---
    sponsor_records = SponsorIncome.objects.filter(date=run_date)
    total_sponsor_income = sum(r.amount for r in sponsor_records)
    sponsor_count = sponsor_records.count()

    # --- IncomeRecord summary ---
    income_records = IncomeRecord.objects.filter(created_at__date=run_date)
    income_total = sum(r.amount for r in income_records)

    # --- Save/Update AuditDailyReport ---
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
        }
    )

    # --- Print audit ---
    print(f"=== All‑in‑One Monitor for {run_date} ===")
    print(f"Processed Members={processed_members}")
    print(f"Eligibility Bonus={total_eligibility_income}")
    print(f"Binary Income={total_binary_income}")
    print(f"Sponsor Income={total_sponsor_income} (Records={sponsor_count})")
    print(f"Flashout Units={flashout_units}")
    print(f"Repurchase Wallet Bonus={total_wallet_income}")
    print(f"Washout Pairs={washout_pairs}")
    print(f"IncomeRecord Total={income_total}")

    print("\n--- SponsorIncome Records ---")
    for record in sponsor_records.select_related("sponsor","child"):
        print(
            f"Sponsor {record.sponsor.member_id} credited ₹{record.amount} "
            f"from Child {record.child.member_id} "
            f"(Eligibility Bonus={record.eligibility_bonus})"
        )

    print("\n--- IncomeRecord Entries ---")
    for rec in income_records.select_related("member"):
        print(
            f"Member {rec.member.member_id} | Eligibility={rec.amount - rec.binary_income - rec.wallet_income} | "
            f"Binary={rec.binary_income} | SponsorMirror={rec.sponsor_income} | "
            f"Wallet={rec.wallet_income} | Total={rec.amount}"
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

