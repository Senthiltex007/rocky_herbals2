from django.db.models import Sum
from datetime import date
from herbalapp.models import Member, SponsorIncome, CommissionRecord, DailyIncomeReport
from herbalapp.mlm_engine_binary import determine_rank_from_bv

def run_full_income_audit():
    print("🔍 Starting Full Income Audit...\n")

    for m in Member.objects.all():
        sponsor_total = SponsorIncome.objects.filter(sponsor=m).aggregate(total=Sum("amount"))["total"] or 0
        binary_total = CommissionRecord.objects.filter(member=m, level="binary").aggregate(total=Sum("amount"))["total"] or 0
        flashout_total = CommissionRecord.objects.filter(member=m, level="flashout").aggregate(total=Sum("amount"))["total"] or 0
        eligibility_total = CommissionRecord.objects.filter(member=m, level="eligibility").aggregate(total=Sum("amount"))["total"] or 0
        repurchase_total = CommissionRecord.objects.filter(member=m, level="repurchase").aggregate(total=Sum("amount"))["total"] or 0

        report = DailyIncomeReport.objects.filter(member=m, date=date.today()).first()
        lifetime_bv = getattr(m, "lifetime_bv", 0)
        rank_info = determine_rank_from_bv(lifetime_bv)
        if rank_info:
            rank_title, monthly_salary, months = rank_info
        else:
            rank_title, monthly_salary, months = ("None", 0, 0)

        if report:
            print(
                f"{m.auto_id} ({m.name}) | Sponsor={sponsor_total} | Binary={binary_total} | Flashout={flashout_total} | "
                f"Eligibility={eligibility_total} | Repurchase={repurchase_total} | Salary={report.salary_income} | Rank={report.rank_title} | "
                f"BV={lifetime_bv} | ExpectedRank={rank_title} ({monthly_salary}×{months}) | L_joins={report.left_joins}, R_joins={report.right_joins}"
            )
        else:
            print(
                f"{m.auto_id} ({m.name}) | Sponsor={sponsor_total} | Binary={binary_total} | Flashout={flashout_total} | "
                f"Eligibility={eligibility_total} | Repurchase={repurchase_total} | BV={lifetime_bv} | ExpectedRank={rank_title} ({monthly_salary}×{months}) | No Daily Report today"

