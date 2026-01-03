# test_mlm_engine.py
from django.utils import timezone
from decimal import Decimal
from herbalapp.models import Member, IncomeRecord, SponsorIncome, DailyIncomeReport
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day

def audit(member_id, run_date):
    print("\n--- Audit for", member_id, "on", run_date, "---")
    print("IncomeRecord:", IncomeRecord.objects.filter(member__auto_id=member_id, date=run_date).count())
    print("SponsorIncome:", SponsorIncome.objects.filter(sponsor__auto_id=member_id, date=run_date).count())
    print("DailyIncomeReport:", DailyIncomeReport.objects.filter(member__auto_id=member_id, date=run_date).count())
    for rec in IncomeRecord.objects.filter(member__auto_id=member_id, date=run_date):
        print("IncomeRecord →", rec.type, rec.amount, rec.binary_income, rec.sponsor_income, rec.wallet_income, rec.eligibility_income)

# ---------- Unlock day simulation ----------
run_date = timezone.now().date()
member = Member.objects.get(auto_id="rocky005")

print("\n⚡ Unlock day simulation (2:1 imbalance)")
result_unlock = calculate_member_binary_income_for_day(
    left_joins_today=2,
    right_joins_today=1,
    left_cf_before=0,
    right_cf_before=0,
    binary_eligible=False,
    member=member,
    run_date=run_date
)
print("Result unlock:", result_unlock)
audit("rocky005", run_date)

# ---------- Normal day simulation ----------
print("\n⚡ Normal day simulation (3 new 1:1 pairs)")
result_normal = calculate_member_binary_income_for_day(
    left_joins_today=3,
    right_joins_today=3,
    left_cf_before=0,
    right_cf_before=0,
    binary_eligible=True,
    member=member,
    run_date=run_date
)
print("Result normal:", result_normal)
audit("rocky005", run_date)

