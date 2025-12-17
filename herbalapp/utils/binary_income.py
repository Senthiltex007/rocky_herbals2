# herbalapp/utils/binary_income.py
from decimal import Decimal
from django.utils import timezone
from herbalapp.models import Member, DailyIncomeReport

# CONFIG
PAIR_AMOUNT = Decimal('500.00')        # ₹500 per matched pair
DAILY_MAX_PAIRS = 5                    # max payable pairs per day (binary)
FLASH_UNIT_VALUE = Decimal('1000.00')  # each flashout unit credited to repurchase wallet
FLASH_UNIT_PAIR = 5                    # pairs per flashout unit (5:5)
FLASH_UNIT_DAILY_MAX = 9               # max flashout units per member per day

def _add_daily_report(
    member: Member,
    date,
    binary: Decimal = Decimal("0.00"),
    sponsor: Decimal = Decimal("0.00"),
    flash: Decimal = Decimal("0.00"),
    salary: Decimal = Decimal("0.00"),
    stock: Decimal = Decimal("0.00"),  # model-ல் இதுக்கு field இல்லை; ignore பண்ணுவோம்
):
    """
    Helper: create or update DailyIncomeReport for member/date மற்றும் total_income update செய்யும்.
    உன் model fields க்கு ஏற்ப map பண்ணிருக்கேன்:

    - binary_income
    - sponsor_income
    - flashout_wallet_income  (old name flash_bonus இல்லை)
    - salary_income           (old name salary இல்லை)
    - total_income
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

    # amounts சேர்க்கும்
    if binary:
        report.binary_income += binary

    if sponsor:
        report.sponsor_income += sponsor

    # ⚠️ உன் model இப்படி தான்:
    # flashout_wallet_income  ← flashout income
    if flash:
        report.flashout_wallet_income += flash

    # salary_income field க்கு map பண்ணணும்
    if salary:
        report.salary_income += salary

    # stock_commission என்ற field நீ model-ல வைத்திருக்கல, அதனால் stock ஐ ignore பண்ணுறோம்.

    # total_income = binary + sponsor + flashout_wallet_income + salary
    report.total_income = (
        report.binary_income
        + report.sponsor_income
        + report.flashout_wallet_income
        + report.salary_income
    )

    report.save()
    return report


def _credit_sponsor_for_binary(earner: Member, binary_amount: Decimal, date):
    """
    Sponsor income rule:
    - earner-க்கு sponsor இருந்தா, sponsor.binary_eligible == True இருந்தா மட்டும்
      sponsor-க்கு binary_amount அளவுக்கு sponsor_income கொடுக்கணும்.
    - sponsor.sponsor_income (Member field) + DailyIncomeReport sponsor_income update ஆகும்.
    """
    if not earner.sponsor or binary_amount <= 0:
        return Decimal("0.00")

    sponsor = earner.sponsor

    # Sponsor must be eligible for binary income (rule)
    if not sponsor.binary_eligible:
        return Decimal("0.00")

    # Credit sponsor profile total sponsor_income
    sponsor.sponsor_income = (sponsor.sponsor_income or Decimal("0.00")) + binary_amount
    sponsor.save(update_fields=["sponsor_income"])

    # Daily report-ல் sponsor_income update
    _add_daily_report(sponsor, date, sponsor=binary_amount)

    return binary_amount

def process_member_binary_income(member: Member):
    """
    Main function:
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

    # இன்று new joins + பழைய carry forward
    left_total = (member.left_new_today or 0) + (member.left_cf or 0)
    right_total = (member.right_new_today or 0) + (member.right_cf or 0)

    # ---------- ONE-TIME ELIGIBILITY CHECK ----------
    if not member.binary_eligible:
        # requirement: at least 1:2 or 2:1
        if (left_total >= 1 and right_total >= 2) or (left_total >= 2 and right_total >= 1):
            # One-time achievement bonus: 1 pair amount
            income_binary += PAIR_AMOUNT

            member.binary_eligible = True
            member.binary_eligible_date = timezone.now()

            # 1 pair consume (1 left + 1 right) if both sides >= 1
            if left_total >= 1 and right_total >= 1:
                left_total -= 1
                right_total -= 1

            member.save(update_fields=["binary_eligible", "binary_eligible_date"])

    # ---------- DAILY BINARY PAIR PAYMENT ----------
    payable_pairs = 0
    if member.binary_eligible:
        matched_pairs_total = min(left_total, right_total)

        # daily cap respect பண்ணி payable pairs
        payable_pairs = min(matched_pairs_total, DAILY_MAX_PAIRS)
        income_binary += Decimal(payable_pairs) * PAIR_AMOUNT

        # binary payout க்கு use பண்ணிய pairs remove பண்ணு
        left_total -= payable_pairs
        right_total -= payable_pairs

    # ---------- FLASHOUT (repurchase) ----------
    matched_pairs_after_binary = min(left_total, right_total)
    flash_units = matched_pairs_after_binary // FLASH_UNIT_PAIR
    usable_units = 0

    if flash_units > 0:
        usable_units = min(flash_units, FLASH_UNIT_DAILY_MAX)
        income_flash = Decimal(usable_units) * FLASH_UNIT_VALUE

        consumed_pairs_for_flash = usable_units * FLASH_UNIT_PAIR
        left_total -= consumed_pairs_for_flash
        right_total -= consumed_pairs_for_flash

    # ---------- CARRY FORWARD ----------
    # CF after binary + flashout
    new_left_cf = max(int(left_total), 0)
    new_right_cf = max(int(right_total), 0)

    # previous CF before this run
    prev_left_cf = member.left_cf or 0
    prev_right_cf = member.right_cf or 0

    # ---------- PERSISTENT ACCOUNT UPDATES ----------
    # Member.binary_income total
    if income_binary > 0:
        member.binary_income = (member.binary_income or Decimal("0.00")) + income_binary

    # repurchase_wallet = flashout income
    if income_flash > 0:
        member.repurchase_wallet = (member.repurchase_wallet or Decimal("0.00")) + income_flash

    # carry forward update
    member.left_cf = new_left_cf
    member.right_cf = new_right_cf

    # ---------- SAVE JOIN COUNTS BEFORE RESET ----------
    left_joins_today = member.left_new_today or 0
    right_joins_today = member.right_new_today or 0

    # இன்று new counts reset (processed already)
    member.left_new_today = 0
    member.right_new_today = 0

    member.save(
        update_fields=[
            "binary_income",
            "repurchase_wallet",
            "left_cf",
            "right_cf",
            "left_new_today",
            "right_new_today",
        ]
    )

    # ---------- DAILY REPORT FULL UPDATE ----------
    report = _add_daily_report(
        member,
        today,
        binary=income_binary,
        flash=income_flash,
    )

    # Joins
    report.left_joins = left_joins_today
    report.right_joins = right_joins_today

    # CF before = previous CF + today's joins
    report.left_cf_before = prev_left_cf + left_joins_today
    report.right_cf_before = prev_right_cf + right_joins_today

    # CF after = new CF
    report.left_cf_after = new_left_cf
    report.right_cf_after = new_right_cf

    # Binary pairs paid
    report.binary_pairs_paid = payable_pairs

    # Flashout units
    report.flashout_units = usable_units

    # Washed pairs (unused flash units)
    report.washed_pairs = max(flash_units - usable_units, 0)

    # BV totals
    report.total_left_bv = member.total_left_bv or 0
    report.total_right_bv = member.total_right_bv or 0

    report.save()

    # ---------- SPONSOR CREDIT ----------
    if income_binary > 0:
        sponsor_credit = _credit_sponsor_for_binary(member, income_binary, today)

    return {
        "binary_income": income_binary,
        "flashout_income": income_flash,
        "sponsor_income_credit": sponsor_credit,
        "left_cf": member.left_cf,
        "right_cf": member.right_cf,
        "binary_eligible": member.binary_eligible,
        "flash_units_used": usable_units,
    }


