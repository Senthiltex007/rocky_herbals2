import os
import django
import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rocky_herbals2.settings")
django.setup()

from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day, determine_rank_from_bv

# ✅ Target date for income calculation
target_date = datetime.date(2025, 12, 15)

print("✅ Running NEW MLM ENGINE for:", target_date)

members = Member.objects.all()

for m in members:
    print("\nProcessing:", m.member_id, m.name)

    # ✅ 1. இன்று அந்த member கீழ் join ஆனவர்களை கணக்கு போடு (left/right)
    left_today = Member.objects.filter(
        parent=m,
        side="L",
        joined_date=target_date,
    ).count()

    right_today = Member.objects.filter(
        parent=m,
        side="R",
        joined_date=target_date,
    ).count()

    # ✅ 2. CF values (before)
    left_cf_before = m.left_cf or 0
    right_cf_before = m.right_cf or 0

    # ✅ 3. Binary engine run
    result = calculate_member_binary_income_for_day(
        left_joins_today=left_today,
        right_joins_today=right_today,
        left_cf_before=left_cf_before,
        right_cf_before=right_cf_before,
        binary_eligible=m.binary_eligible,
    )

    print("Engine result:", result)

    # -------------------------------
    # ✅ 4. Lifetime eligibility date update (1:2 / 2:1 once)
    # -------------------------------
    eligibility_income = result["eligibility_income"]

    if (not m.binary_eligible) and result["new_binary_eligible"]:
        m.binary_eligible = True
        # ஒரே முறை eligibility date save
        if m.binary_eligible_date is None:
            m.binary_eligible_date = timezone.now()
        m.save(update_fields=["binary_eligible", "binary_eligible_date"])
        print("👉 Eligibility ACTIVATED for", m.member_id, "on", m.binary_eligible_date)

    # -------------------------------
    # ✅ 5. Sponsor income (ONE-TIME 1:1 lifetime achievement rule)
    # -------------------------------
    sponsor_income = 0
    sponsor_eligible = False

    if m.sponsor:  # sponsor exists
        sponsor = m.sponsor

        # Sponsor must be binary eligible
        if sponsor.binary_eligible:
            # Lifetime legs for sponsor
            sponsor_total_left = (sponsor.left_cf or 0) + (sponsor.left_join_count or 0)
            sponsor_total_right = (sponsor.right_cf or 0) + (sponsor.right_join_count or 0)

            # ONE-TIME 1:1 condition (lifetime)
            if sponsor_total_left >= 1 and sponsor_total_right >= 1:
                sponsor_eligible = True
                # sponsor gets fixed percentage of member's binary income (for example 10%)
                sponsor_income = result["binary_income"] * 0.10

    # ✅ Sponsor income round பண்ணி (float → int)
    sponsor_income = int(round(sponsor_income))

    # -------------------------------
    # ✅ 6. Rank & salary from BV
    # -------------------------------
    # Lifetime BV
    total_left_bv = m.total_left_bv or 0
    total_right_bv = m.total_right_bv or 0
    total_bv = min(total_left_bv, total_right_bv)

    rank_title = m.rank or "Starter"
    salary_income = m.salary or 0

    rank_info = determine_rank_from_bv(total_bv)
    if rank_info is not None:
        rank_title, monthly_salary, months = rank_info
        salary_income = monthly_salary  # simple: pay full monthly salary per qualifying day

    # -------------------------------
    # ✅ 7. Final income aggregation for the day
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
    # ✅ 8. Update Member carry forward & wallets
    # -------------------------------
    m.left_cf = result["left_cf_after"]
    m.right_cf = result["right_cf_after"]

    # Wallet updates (simple example, customize as per your real plan)
    m.binary_income += binary_income
    m.flash_bonus += flashout_income
    m.sponsor_income += sponsor_income
    m.salary += salary_income
    m.main_wallet += total_income_for_day

    # Rank update
    m.rank = rank_title

    m.save()

    # -------------------------------
    # ✅ 9. Update DailyIncomeReport
    # -------------------------------
    report, created = DailyIncomeReport.objects.get_or_create(
        member=m,
        date=target_date,
    )

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

    print(f"👉 {m.member_id} | Total income for {target_date}: {total_income_for_day}")

print("\n✅ NEW MLM ENGINE RUN COMPLETED ✅")

