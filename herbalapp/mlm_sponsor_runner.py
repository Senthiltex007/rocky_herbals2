from datetime import date
from django.utils import timezone
from decimal import Decimal
from herbalapp.models import Member, SponsorIncome, DailyIncomeReport
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day


def run_daily_binary_and_sponsor(member: Member, left_joins_today: int, right_joins_today: int):

    today = date.today()

    # ✅ CF snapshot before calculation
    left_cf_before = member.left_cf
    right_cf_before = member.right_cf

    # -----------------------------
    # 1. Run binary engine
    # -----------------------------
    result = calculate_member_binary_income_for_day(
        left_joins_today=left_joins_today,
        right_joins_today=right_joins_today,
        left_cf_before=member.left_cf,
        right_cf_before=member.right_cf,
        binary_eligible=member.binary_eligible,
    )

    eligibility_income = Decimal(result["eligibility_income"])
    binary_income = Decimal(result["binary_income"])
    total_income = Decimal(result["total_income"])
    child_total_for_sponsor = Decimal(result["child_total_for_sponsor"])

    # -----------------------------
    # 2. Update eligibility
    # -----------------------------
    if result["new_binary_eligible"] and not member.binary_eligible:
        member.binary_eligible = True
        member.binary_eligible_date = timezone.now()

    # -----------------------------
    # 3. Update first 1:1 pair flag
    # -----------------------------
    if result["binary_pairs"] > 0 and not member.has_completed_first_pair:
        member.has_completed_first_pair = True

    # -----------------------------
    # 4. Update CF
    # -----------------------------
    member.left_cf = result["left_cf_after"]
    member.right_cf = result["right_cf_after"]
    member.save()

    # -----------------------------
    # 5. Sponsor Income Logic
    # -----------------------------
    sponsor_income_amount = Decimal("0.00")
    sponsor = member.sponsor

    if sponsor and child_total_for_sponsor > 0:
        if sponsor.has_completed_first_pair:
            sponsor_income_amount = child_total_for_sponsor

            SponsorIncome.objects.create(
                sponsor=sponsor,
                child=member,
                amount=sponsor_income_amount,
                date=today
            )

    # -----------------------------
    # 6. Save Daily Income Report (SAFE + MODEL MATCHED)
    # -----------------------------
    report, created = DailyIncomeReport.objects.get_or_create(
        member=member,
        date=today,
        defaults={
            "left_joins": left_joins_today,
            "right_joins": right_joins_today,
            "left_cf_before": left_cf_before,
            "right_cf_before": right_cf_before,
            "left_cf_after": result["left_cf_after"],
            "right_cf_after": result["right_cf_after"],
            "binary_pairs_paid": result["binary_pairs"],
            "binary_income": binary_income,
            "sponsor_income": sponsor_income_amount,
            "total_income": total_income,
        }
    )

    if not created:
        report.left_joins += left_joins_today
        report.right_joins += right_joins_today

        report.left_cf_before = left_cf_before
        report.right_cf_before = right_cf_before
        report.left_cf_after = result["left_cf_after"]
        report.right_cf_after = result["right_cf_after"]

        report.binary_pairs_paid += result["binary_pairs"]
        report.binary_income += binary_income
        report.sponsor_income += sponsor_income_amount
        report.total_income += total_income

        report.save()

    return {
        "child_result": result,
        "sponsor_income": sponsor_income_amount,
    }

