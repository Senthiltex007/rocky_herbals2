# test_mlm_income.py
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport
from herbalapp.management.commands.mlm_run_daily_income import process_member_daily_income

from decimal import Decimal

today = timezone.now().date()

# --------------------------
# CLEAN EXISTING DATA
# --------------------------
DailyIncomeReport.objects.filter(date=today).delete()
Member.objects.all().delete()

# --------------------------
# CREATE TEST MEMBERS
# --------------------------
root = Member.objects.create(auto_id="rocky001", name="Root")
p = Member.objects.create(auto_id="rocky002", name="Placement Parent", parent=root)
s = Member.objects.create(auto_id="rocky003", name="Sponsor", parent=p)
c = Member.objects.create(auto_id="rocky004", name="Child", parent=s)

members = [root, p, s, c]
print(f"✅ {len(members)} members recreated")

# --------------------------
# RESET MEMBER STATES
# --------------------------
for m in members:
    m.binary_eligible = False
    m.left_carry_forward = 0
    m.right_carry_forward = 0
    m.left_joins_today = 0
    m.right_joins_today = 0
    m.income = Decimal("0")
    m.save()

# --------------------------
# SIMULATE TODAY JOINS
# --------------------------
# Example: child joins today
c.left_joins_today = 1
c.right_joins_today = 2
c.save()

# Example: sponsor joins today (optional)
s.left_joins_today = 1
s.right_joins_today = 1
s.save()

# --------------------------
# RUN DAILY INCOME ENGINE
# --------------------------
print("✅ Running MLM income calculation...")
for m in Member.objects.all():
    process_member_daily_income(m, today)

# --------------------------
# SHOW RESULTS
# --------------------------
reports = DailyIncomeReport.objects.filter(date=today).values(
    "member__auto_id",
    "binary_income",
    "flashout_wallet_income",
    "sponsor_income",
    "total_income",
    "left_cf_before",
    "right_cf_before",
    "left_cf_after",
    "right_cf_after",
    "binary_pairs_paid",
    "flashout_units",
    "washed_pairs",
)

print("\n--- DAILY INCOME REPORT ---")
for r in reports:
    print(r)

print("\n✅ MLM income test completed successfully")

