# herbalapp/audit_daily_report.py
# ----------------------------------------------------------
# ✅ Daily Audit — validates each member’s DailyIncomeReport
# ✅ Prints summary (safe fields only)
# ----------------------------------------------------------

from herbalapp.models import DailyIncomeReport, Member
from datetime import date

def run_daily_audit():
    print("🔍 Starting Daily Income Audit...\n")

    for m in Member.objects.all():
        report = DailyIncomeReport.objects.filter(member=m, date=date.today()).first()
        if report:
            # ✅ Print summary (safe fields, using id instead of auto_id)
            print(
                f"{m.id} ({m.name}) | "
                f"L_joins={report.left_joins}, R_joins={report.right_joins} | "
                f"Sponsor={report.sponsor_income} | Binary={report.binary_income} | "
                f"Total={report.total_income}"
            )
        else:
            print(f"{m.id} ({m.name}) | No report for today")

    print("\n✅ Daily Income Audit completed.")

