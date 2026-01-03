# audit_income.py
from herbalapp.models import IncomeReport, SponsorIncome, BinaryIncome

def audit_member_income(member_id, date):
    print(f"--- Audit for {member_id} on {date} ---")

    # IncomeReport check
    reports = IncomeReport.objects.filter(member__auto_id=member_id, date=date)
    for r in reports:
        print("IncomeReport:", r.member.auto_id, r.date,
              "Binary:", r.binary_income,
              "Sponsor:", r.sponsor_income,
              "Wallet:", r.wallet_income,
              "Salary:", r.salary_income,
              "Total:", r.total_income)
    print("IncomeReport count:", reports.count())

    # SponsorIncome check
    sponsors = SponsorIncome.objects.filter(receiver__auto_id=member_id, date=date)
    for s in sponsors:
        print("SponsorIncome:", s.receiver.auto_id, s.date, "Amount:", s.amount)
    print("SponsorIncome count:", sponsors.count())

    # BinaryIncome check
    binaries = BinaryIncome.objects.filter(member__auto_id=member_id, date=date)
    for b in binaries:
        print("BinaryIncome:", b.member.auto_id, b.date, "Amount:", b.amount)
    print("BinaryIncome count:", binaries.count())

# Run audit for rocky005 on Dec 31, 2025
audit_member_income("rocky005", "2025-12-31")

