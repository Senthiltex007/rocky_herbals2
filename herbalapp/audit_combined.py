from django.db.models import Sum
from datetime import date
from herbalapp.models import Member, SponsorIncome, CommissionRecord, DailyIncomeReport

def run_combined_audit():
    print("🔍 Starting Combined Audit...\n")

    for m in Member.objects.all():
        report = DailyIncomeReport.objects.filter(member=m, date=date.today()).first()

        sponsor_total = SponsorIncome.objects.filter(sponsor=m).aggregate(total=Sum("amount"))["total"] or 0
        binary_total = CommissionRecord.objects.filter(member=m, level="binary").aggregate(total=Sum("amount"))["total"] or 0
        flashout_total = CommissionRecord.objects.filter(member=m, level="flashout").aggregate(total=Sum("amount"))["total"] or 0
        eligibility_total = CommissionRecord.objects.filter(member=m, level="eligibility").aggregate(total=Sum("amount"))["total"] or 0
        repurchase_total = CommissionRecord.objects.filter(member=m, level="repurchase").aggregate(total=Sum("amount"))["total"] or 0

        if report:
            print(
                f"{m.id} ({m.name}) | "
                f"Daily: L={report.left_joins}, R={report.right_joins}, Sponsor={report.sponsor_income}, Binary={report.binary_income}, Total={report.total_income} || "
                f"Lifetime: Sponsor={sponsor_total}, Binary={binary_total}, Flashout={flashout_total}, Eligibility={eligibility_total}, Repurchase={repurchase_total}"
            )
        else:
            print(
                f"{m.id} ({m.name}) | No Daily Report today || "
                f"Lifetime: Sponsor={sponsor_total}, Binary={binary_total}, Flashout={flashout_total}, Eligibility={eligibility_total}, Repurchase={repurchase_total}"
            )

    print("\n✅ Combined Audit completed.")

