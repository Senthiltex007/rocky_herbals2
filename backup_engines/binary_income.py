# herbalapp/utils/binary_income.py
from decimal import Decimal
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport, SponsorIncome

# CONFIG
PAIR_AMOUNT = Decimal('500.00')        # ₹500 per matched pair
DAILY_MAX_PAIRS = 5                    # max payable pairs per day (binary)
FLASH_UNIT_VALUE = Decimal('1000.00')  # each flashout unit credited to repurchase wallet
FLASH_UNIT_PAIR = 5                    # pairs per flashout unit (5:5)
FLASH_UNIT_DAILY_MAX = 9               # max flashout units per member per day
ELIGIBLE_BONUS = Decimal('500.00')     # one-time eligibility bonus


def _add_daily_report(
    member: Member,
    date,
    binary: Decimal = Decimal("0.00"),
    sponsor: Decimal = Decimal("0.00"),
    flash: Decimal = Decimal("0.00"),
    salary: Decimal = Decimal("0.00"),
):
    """
    Helper: create or update DailyIncomeReport for member/date மற்றும் total_income update செய்யும்.
    """
    report, created = DailyIncomeReport.objects.get_or_create(
        member=member,
        date=date,
        defaults={
            "left_joins": 0,
            "right_joins": 0,
            "left_cf_before": 0,
            "right_cf_before": 0,
            "left_cf_after": 0,
            "right_cf_after": 0,
            "binary_pairs_paid": 0,
            "binary_income": Decimal("0.00"),
            "flashout_units": 0,
            "flashout_wallet_income": Decimal("0.00"),
            "washed_pairs": 0,
            "total_left_bv": 0,
            "total_right_bv": 0,
            "salary_income": Decimal("0.00"),
            "rank_title": "",
            "sponsor_income": Decimal("0.00"),
            "total_income": Decimal("0.00"),
        },
    )

    if binary:
        report.binary_income += binary
    if sponsor:
        report.sponsor_income += sponsor
    if flash:
        report.flashout_wallet_income += flash
    if salary:
        report.salary_income += salary

    report.total_income = (
        report.binary_income
        + report.sponsor_income
        + report.flashout_wallet_income
        + report.salary_income
    )

    report.save()
    return report


def _credit_sponsor_for_binary(earner: Member, binary_amount: Decimal, date, eligibility_bonus: Decimal = Decimal("0.00")):
    """
    Sponsor income rules:
    - Rule #1: If placement == sponsor → income goes to placement.sponsor (parent). Fallback to sponsor if missing.
    - Rule #2: Else → income goes to sponsor.
    - Rule #3: Receiver must be binary_eligible (or lifetime pairs >= 1).
    - Amount = binary_amount + eligibility_bonus (eligibility day mirror).
    """
    if not earner.sponsor or (binary_amount + eligibility_bonus) <= 0:
        return Decimal("0.00")

    sponsor_receiver = None
    if earner.sponsor == earner.placement:
        sponsor_receiver = earner.placement.sponsor or earner.sponsor
    else:
        sponsor_receiver = earner.sponsor

    if not sponsor_receiver:
        return Decimal("0.00")

    # Eligibility gate
    if not sponsor_receiver.binary_eligible:
        return Decimal("0.00")

    sponsor_income_amount = binary_amount + eligibility_bonus

    # Credit sponsor profile
    sponsor_receiver.sponsor_income = (sponsor_receiver.sponsor_income or Decimal("0.00")) + sponsor_income_amount
    sponsor_receiver.save(update_fields=["sponsor_income"])

    # Daily report update
    _add_daily_report(sponsor_receiver, date, sponsor=sponsor_income_amount)

    # SponsorIncome record
    SponsorIncome.objects.get_or_create(
        sponsor=sponsor_receiver,
        child=earner,
        date=date,
        defaults={"amount": sponsor_income_amount}
    )

    return sponsor_income_amount


def process_member_binary_income(member: Member):
    """
    Main function:
    - eligibility bonus
    - binary income
    - flashout (repurchase wallet)
    - sponsor credit
    - carry-forward
    - DailyIncomeReport update
    """

    today = timezone.now().date()
    income_binary = Decimal("0.00")
    income_flash = Decimal("0.00")
    sponsor_credit = Decimal("0.00")
    eligibility_bonus = Decimal("0.00")

    left_total = (member.left_new_today or 0) + (member.left_cf or 0)
    right_total = (member.right_new_today or 0) + (member.right_cf or 0)

    # ---------- ONE-TIME ELIGIBILITY CHECK ----------
    if not member.binary_eligible:
        if (left_total >= 1 and right_total >= 2) or (left_total >= 2 and right_total >= 1):
            eligibility_bonus = ELIGIBLE_BONUS
            income_binary += eligibility_bonus

            member.binary_eligible = True
            member.binary_eligible_date = timezone.now()

            if left_total >= 1 and right_total >= 1:
                left_total -= 1
                right_total -= 1

            member.save(update_fields=["binary_eligible", "binary_eligible_date"])

    # ---------- DAILY BINARY PAIR PAYMENT ----------
    payable_pairs = 0
    if member.binary_eligible:
        matched_pairs_total = min(left_total, right_total)
        payable_pairs = min(matched_pairs_total, DAILY_MAX_PAIRS)
        income_binary += Decimal(payable_pairs) * PAIR_AMOUNT
        left_total -= payable_pairs
        right_total -= payable_pairs

    # ---------- FLASHOUT ----------
    matched_pairs_after_binary = min(left_total, right_total)
    flash_units = matched_pairs_after_binary // FLASH_UNIT_PAIR
    usable_units = min(flash_units, FLASH_UNIT_DAILY_MAX)
    if usable_units > 0:
        income_flash = Decimal(usable_units) * FLASH_UNIT_VALUE
        consumed_pairs_for_flash = usable_units * FLASH_UNIT_PAIR
        left_total -= consumed_pairs_for_flash
        right_total -= consumed_pairs_for_flash

    # ---------- CARRY FORWARD ----------
    new_left_cf = max(int(left_total), 0)
    new_right_cf = max(int(right_total), 0)
    prev_left_cf = member.left_cf or 0
    prev_right_cf = member.right_cf or 0

    if income_binary > 0:
        member.binary_income = (member.binary_income or Decimal("0.00")) + income_binary
    if income_flash > 0:
        member.repurchase_wallet = (member.repurchase_wallet or Decimal("0.00")) + income_flash

    member.left_cf = new_left_cf
    member.right_cf = new_right_cf
    left_joins_today = member.left_new_today or 0
    right_joins_today = member.right_new_today or 0
    member.left_new_today = 0
    member.right_new_today = 0

    member.save(update_fields=[
        "binary_income", "repurchase_wallet",
        "left_cf", "right_cf",
        "left_new_today", "right_new_today"
    ])

    # ---------- DAILY REPORT ----------
    report = _add_daily_report(member, today, binary=income_binary, flash=income_flash)
    report.left_joins = left_joins_today
    report.right_joins = right_joins_today
    report.left_cf_before = prev_left_cf + left_joins_today
    report.right_cf_before = prev_right_cf + right_joins_today
    report.left_cf_after = new_left_cf
    report.right_cf_after = new_right_cf
    report.binary_pairs_paid = payable_pairs
    report.flashout_units = usable_units
    report.washed_pairs = max(flash_units - usable_units, 0)
    report.total_left_bv = member.total_left_bv or 0
    report.total_right_bv = member.total_right_bv or 0
    report.save()

    # ---------- SPONSOR CREDIT ----------
    if income_binary > 0 or eligibility_bonus > 0:
        sponsor_credit = _credit_sponsor_for_binary(member, income_binary - eligibility_bonus, today, eligibility_bonus)

    return {
        "binary_income": income_binary,
        "flashout_income": income_flash,
        "sponsor_income_credit": sponsor_credit,
        "left_cf": member.left_cf,
        "right_cf": member.right_cf,
        "binary_eligible": member.binary_eligible,
        "flash_units_used": usable_units,
        "eligibility_bonus": eligibility_bonus,
    }

