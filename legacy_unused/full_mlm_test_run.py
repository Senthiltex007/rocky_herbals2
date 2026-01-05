# full_mlm_test_run.py
# ----------------------------------------------------------
# MLM Daily Engine Test Script
# Run manually to reset incomes, setup test tree, and check all reports
# ----------------------------------------------------------

from datetime import date
from herbalapp.models import Member, DailyIncomeReport, SponsorIncome
from herbalapp.engine.run import process_member_daily

# ----------------------------------------------------------
# Step 0: Clean previous test data
# ----------------------------------------------------------
DailyIncomeReport.objects.all().delete()
SponsorIncome.objects.all().delete()
print("✅ Deleted all previous Daily & Sponsor Income records")

# ----------------------------------------------------------
# Step 1: Reset binary eligibility for all members
# ----------------------------------------------------------
Member.objects.update(
    binary_eligible=False,
    binary_eligible_date=None
)
print("✅ Reset binary eligibility for all members")

# ----------------------------------------------------------
# Step 2: Setup test scenario for Rocky001
# ----------------------------------------------------------
root_member = Member.objects.get(auto_id="rocky001")

# Create left & right child to form binary pair if not exist
left_child, _ = Member.objects.get_or_create(
    auto_id="test_left_01",
    defaults={
        "name": "Left Test Child",
        "placement": root_member,
        "position": "left",
        "sponsor": root_member,
        "joined_date": date(2025, 12, 23),
    }
)

right_child, _ = Member.objects.get_or_create(
    auto_id="test_right_01",
    defaults={
        "name": "Right Test Child",
        "placement": root_member,
        "position": "right",
        "sponsor": root_member,
        "joined_date": date(2025, 12, 23),
    }
)

# Make root member binary eligible for the test
root_member.binary_eligible = True
root_member.binary_eligible_date = date(2025, 12, 23)
root_member.save()
print("✅ Test children ready and root member set as binary eligible")

# ----------------------------------------------------------
# Step 3: Run MLM Engine manually for all root members
# ----------------------------------------------------------
run_date = date(2025, 12, 23)
for root in Member.objects.filter(placement__isnull=True):
    try:
        process_member_daily(root, run_date)
        print(f"✅ Engine run completed for {root.auto_id}")
    except Exception as e:
        print(f"⚠️ Engine failed for {root.auto_id}: {e}")

# ----------------------------------------------------------
# Step 4: Check Daily Income Report
# ----------------------------------------------------------
print("\n✅ Daily Income Reports:")
for d in DailyIncomeReport.objects.all():
    print({
        "auto_id": d.member.auto_id,
        "name": d.member.name,
        "eligible_bonus": getattr(d, 'eligible_bonus', 0),
        "binary_income": getattr(d, 'binary_income', 0),
        "sponsor_income": getattr(d, 'sponsor_income', 0),
        "flashout_income": getattr(d, 'flashout_income_repurchase_wallet', 0),
        "carry_forward_left": getattr(d, 'carry_forward_left', 0),
        "carry_forward_right": getattr(d, 'carry_forward_right', 0),
        "washout_pairs": getattr(d, 'washout_pairs', 0),
        "total_direct_income": getattr(d, 'total_direct_income', 0)
    })

# ----------------------------------------------------------
# Step 5: Check Sponsor Income Report
# ----------------------------------------------------------
print("\n✅ Sponsor Income Reports:")
for s in SponsorIncome.objects.all():
    print({
        "auto_id": s.member.auto_id,
        "name": s.member.name,
        "sponsor_income": getattr(s, 'sponsor_income', 0)
    })

print("\n✅ Full MLM test run completed")

