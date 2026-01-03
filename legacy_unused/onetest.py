from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day
from herbalapp.models import Member, IncomeRecord, SponsorIncome
import datetime

member = Member.objects.get(auto_id="rocky009")
run_date = datetime.date(2025, 12, 28)

print("=== First run ===")
result1 = calculate_member_binary_income_for_day(
    left_joins_today=1,
    right_joins_today=2,
    left_cf_before=0,
    right_cf_before=0,
    binary_eligible=False,
    member=member,
    run_date=run_date
)
print("Result1:", result1)

print("=== Second run (duplicate attempt) ===")
result2 = calculate_member_binary_income_for_day(
    left_joins_today=0,
    right_joins_today=0,
    left_cf_before=0,
    right_cf_before=0,
    binary_eligible=True,
    member=member,
    run_date=run_date
)
print("Result2:", result2)

print("=== Audit Rocky002 IncomeRecord ===")
print(IncomeRecord.objects.filter(
    member__auto_id="rocky002",
    created_at__date=run_date
).values("eligibility_income","binary_income","sponsor_income","total_income"))

print("=== Audit Rocky009 IncomeRecord ===")
print(IncomeRecord.objects.filter(
    member__auto_id="rocky009",
    created_at__date=run_date
).values("eligibility_income","binary_income","total_income"))

print("=== SponsorIncome routed ===")
print(SponsorIncome.objects.filter(
    sponsor__auto_id="rocky002",
    child__auto_id="rocky009",
    date=run_date
).values("amount","child_id","sponsor_id","date"))

