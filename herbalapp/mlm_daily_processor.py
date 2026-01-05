# herbalapp/mlm_daily_processor.py

for member in all_members:
    if is_dummy_root(member):
        continue


from datetime import date
from decimal import Decimal
from herbalapp.models import Member, IncomeRecord, DailyIncomeReport
from herbalapp.sponsor_engine import process_sponsor_income
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day

def process_daily_income(run_date=None):
    """
    Process all members for ONE DAY:
    - Compute binary income, flashout bonus
    - Update carry forward left/right
    - Credit sponsor income
    - Update DailyIncomeReport and IncomeRecord
    """

    if run_date is None:
        run_date = date.today()

    all_members = Member.objects.all().order_by('id')  # Top-down processing
    results_summary = []

    for member in all_members:
        # Get yesterday carry forward
        try:
            yesterday_report = DailyIncomeReport.objects.filter(
                member=member,
                date__lt=run_date
            ).order_by('-date').first()
            left_cf_before = yesterday_report.left_cf_after if yesterday_report else 0
            right_cf_before = yesterday_report.right_cf_after if yesterday_report else 0
        except Exception:
            left_cf_before = 0
            right_cf_before = 0

        # Today's joins (newly added children under left/right)
        left_joins_today = member.left_children.count()  # Replace with actual logic
        right_joins_today = member.right_children.count()  # Replace with actual logic

        # Existing eligibility
        binary_eligible = member.binary_eligible

        # Compute daily binary
        binary_result = calculate_member_binary_income_for_day(
            left_joins_today=left_joins_today,
            right_joins_today=right_joins_today,
            left_cf_before=left_cf_before,
            right_cf_before=right_cf_before,
            binary_eligible=binary_eligible
        )

        # Update member's eligibility if changed
        member.binary_eligible = binary_result['new_binary_eligible']
        member.total_left_bv = (member.total_left_bv or 0) + left_joins_today
        member.total_right_bv = (member.total_right_bv or 0) + right_joins_today
        member.total_bv = (member.total_left_bv or 0) + (member.total_right_bv or 0)
        member.save()

        # -------------------------------
        # Create / Update IncomeRecord
        # -------------------------------
        rec, created = IncomeRecord.objects.get_or_create(
            member=member,
            created_at=run_date,
            defaults={
                "binary_pairs": binary_result['binary_pairs_paid'],
                "binary_income": binary_result['binary_income'],
                "flashout_income": binary_result['flashout_income'],
                "sponsor_income": 0,
                "total_income": binary_result['total_income'],
            }
        )
        if not created:
            rec.binary_pairs += binary_result['binary_pairs_paid']
            rec.binary_income += binary_result['binary_income']
            rec.flashout_income += binary_result['flashout_income']
            rec.total_income += binary_result['total_income']
            rec.save()

        # -------------------------------
        # Update DailyIncomeReport
        # -------------------------------
        daily_report, created = DailyIncomeReport.objects.get_or_create(
            member=member,
            date=run_date,
            defaults={
                "eligibility_income": Decimal("0.00"),
                "binary_income": Decimal(binary_result['binary_income']),
                "sponsor_income": Decimal("0.00"),
                "wallet_income": Decimal("0.00"),
                "salary_income": Decimal("0.00"),
                "total_income": Decimal(binary_result['total_income']),
                "left_cf_after": binary_result['left_cf_after'],
                "right_cf_after": binary_result['right_cf_after'],
                "binary_pairs_paid": binary_result['binary_pairs_paid'],
                "flashout_units": binary_result['flashout_units'],
                "flashout_pairs_used": binary_result['flashout_pairs_used'],
                "washed_pairs": binary_result['washed_pairs'],
            }
        )
        if not created:
            daily_report.binary_income += Decimal(binary_result['binary_income'])
            daily_report.total_income += Decimal(binary_result['total_income'])
            daily_report.left_cf_after = binary_result['left_cf_after']
            daily_report.right_cf_after = binary_result['right_cf_after']
            daily_report.binary_pairs_paid += binary_result['binary_pairs_paid']
            daily_report.flashout_units += binary_result['flashout_units']
            daily_report.flashout_pairs_used += binary_result['flashout_pairs_used']
            daily_report.washed_pairs += binary_result['washed_pairs']
            daily_report.save()

        # -------------------------------
        # Process Sponsor Income
        # -------------------------------
        si_amount = process_sponsor_income(
            child_member=member,
            run_date=run_date,
            child_became_eligible_today=binary_result['new_binary_eligible'] and not binary_eligible
        )

        results_summary.append({
            "member": member.auto_id,
            "binary_income": binary_result['binary_income'],
            "flashout_income": binary_result['flashout_income'],
            "total_income": binary_result['total_income'],
            "sponsor_income": si_amount or 0,
        })

    return results_summary


# -------------------------------
# Usage example:
# -------------------------------
# from herbalapp.mlm_daily_processor import process_daily_income
# summary = process_daily_income(date(2026, 1, 4))
# for item in summary:
#     print(item)

