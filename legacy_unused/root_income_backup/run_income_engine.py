import os
import django
import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rocky_herbals2.settings")
django.setup()

from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport
from herbalapp.mlm_engine_binary import (
    calculate_member_binary_income_for_day,
    determine_rank_from_bv
)

# ✅ Target date
target_date = datetime.date(2025, 12, 15)
print("✅ Running MLM ENGINE for:", target_date)

members = Member.objects.all()

for m in members:
    print("\nProcessing:", m.auto_id, m.name)

    # 🔒 Check duplicate run protection
    report, created = DailyIncomeReport.objects.get_or_create(
        member=m,
        date=target_date
    )

    if not created:
        print("⚠️ Income already calculated for this date — SKIPPED")
        continue   # ⛔ VERY IMPORTANT

    # -------------------------------
    # 1️⃣ Today joins
    # -------------------------------
    left_today = Member.objects.filter(
        parent=m, side="L", joined_date=target_date
    ).count()

    right_today = Member.objects.filter(
        parent=m, side="R", joined_date=target_date
    ).count()

    # -------------------------------
    # 2️⃣ Carry forward before
    # -------------------------------
    left_cf_before = m.left_cf or 0
    right_cf_before = m.right_cf or 0

    # -------------------------------
    # 3️⃣ Binary engine
    # -------------------------------
    result = calculate_member_binary_income_for_day(
        left_joins_today=left_today,
        right_joins_today=right_today,
        left_cf_before=left_cf_before,
        right_cf_before=right_cf_before,
        binary_eligible=m.binary_eligible,
    )

    # -------------------------------
    # 4️⃣ Binary eligibility (ONE TIME)
    # -------------------------------
    eligibility_income = result["eligibility_income"]

    if not m.binary_eligible and result["new_binary_eligible"]:
        m.binary_eligible = True
        if not m.binary_eligible_date:
            m.binary_eligible_date = timezone.now()

    # -------------------------------
    # 5️⃣ Sponsor income (ONE TIME RULE)
    # -------------------------------
    sponsor_income = 0
    if m.sponsor and m.sponsor.binary_eligible:
        sponsor = m.sponsor
        if (sponsor.left_cf or 0) >= 1 and (sponsor.right_cf or 0) >= 1:
            sponsor_income = int(result["binary_income"] * 0.10)

    # -------------------------------
    # 6️⃣ Rank & salary
    # -------------------------------
    total_left_bv = m.total_left_bv or 0
    total_right_bv = m.total_right_bv or 0
    total_bv = min(total_left_bv, total_right_bv)

    rank_title = m.rank or "Starter"
    salary_income = 0

    rank_info = determine_rank_from_bv(total_bv)
    if rank_info:
        rank_title, monthly_salary, _ = rank_info
        salary_income = monthly_salary

    # -------------------------------
    # 7️⃣ Total income
    # -------------------------------
    binary_income = result["binary_income"]
    flashout_income = result["flashout_income"]

    total_income_for_day = (
        eligibility_income +
        binary_income +
        flashout_income +
        sponsor_income +
        salary_income
    )

    # -------------------------------
    # 8️⃣ Update member wallets (SAFE)
    # -------------------------------
    m.left_cf = result["left_cf_after"]
    m.right_cf = result["right_cf_after"]

    m.binary_income += binary_income
    m.flash_bonus += flashout_income
    m.sponsor_income += sponsor_income
    m.salary += salary_income
    m.main_wallet += total_income_for_day
    m.rank = rank_title

    m.save()

    # -------------------------------
    # 9️⃣ Save DailyIncomeReport
    # -------------------------------
    report.left_joins = left_today
    report.right_joins = right_today
    report.left_cf_before = left_cf_before
    report.right_cf_before = right_cf_before
    report.left_cf_after = result["left_cf_after"]
    report.right_cf_after = result["right_cf_after"]
    report.binary_pairs_paid = result["binary_pairs_paid"]
    report.binary_income = binary_income
    report.flashout_units = result["flashout_units"]
    report.flashout_wallet_income = flashout_income
    report.washed_pairs = result["washed_pairs"]
    report.total_left_bv = total_left_bv
    report.total_right_bv = total_right_bv
    report.salary_income = salary_income
    report.rank_title = rank_title
    report.sponsor_income = sponsor_income
    report.total_income = total_income_for_day
    report.save()

    print(f"✅ {m.auto_id} income added: ₹{total_income_for_day}")

print("\n🎯 MLM ENGINE COMPLETED SAFELY 🎯")

