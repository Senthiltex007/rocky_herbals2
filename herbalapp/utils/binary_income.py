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

def _add_daily_report(member: Member, date, binary=Decimal('0.00'), sponsor=Decimal('0.00'),
                      flash=Decimal('0.00'), salary=Decimal('0.00'), stock=Decimal('0.00')):
    """Helper: create or update DailyIncomeReport for member/date and update total_income."""
    report, created = DailyIncomeReport.objects.get_or_create(
        member=member,
        date=date,
        defaults={
            'binary_income': Decimal('0.00'),
            'sponsor_income': Decimal('0.00'),
            'flash_bonus': Decimal('0.00'),
            'salary': Decimal('0.00'),
            'stock_commission': Decimal('0.00'),
            'total_income': Decimal('0.00'),
        }
    )

    # Add amounts
    if binary:
        report.binary_income += binary
    if sponsor:
        report.sponsor_income += sponsor
    if flash:
        report.flash_bonus += flash
    if salary:
        report.salary += salary
    if stock:
        report.stock_commission += stock

    # Recompute total (simple sum of columns we track)
    report.total_income = (
        report.binary_income + report.sponsor_income + report.flash_bonus +
        report.salary + report.stock_commission
    )
    report.save()
    return report

def _credit_sponsor_for_binary(earner: Member, binary_amount: Decimal, date):
    """
    Sponsor income rule:
    - If earner has a sponsor (earner.sponsor), and that sponsor is binary_eligible,
      credit the sponsor the same amount as sponsor_income (binary part only).
    - Update sponsor.sponsor_income and DailyIncomeReport for sponsor.
    """
    if not earner.sponsor or binary_amount <= 0:
        return Decimal('0.00')

    sponsor = earner.sponsor

    # Sponsor must be eligible for binary income (rule)
    if not sponsor.binary_eligible:
        return Decimal('0.00')

    # Credit sponsor
    sponsor.sponsor_income = (sponsor.sponsor_income or Decimal('0.00')) + binary_amount
    sponsor.save(update_fields=['sponsor_income'])

    # Update daily report for sponsor
    _add_daily_report(sponsor, date, sponsor=binary_amount)

    return binary_amount

def process_member_binary_income(member: Member):
    """
    Main function to process binary income, flashout (repurchase), sponsor credit,
    carry-forward, and daily report.

    Rules implemented (as per spec):
    - One-time eligibility: 1:2 or 2:1 (if not eligible yet)
    - After eligible: daily 1:1 pairs => ₹500 per pair
    - Daily binary cap: 5 pairs (₹2,500)
    - Carry-forward: unmatched members on heavier side are carried forward to next day
    - Flashout: matched pairs beyond the daily paid binary pairs -> groups of 5 pairs
                form flashout units. Each flashout unit credit = ₹1,000 to repurchase_wallet.
                Flashout units capped to 9/day. Excess units washout (no credit).
    - Sponsor income: when a member receives binary payout (binary_amount > 0),
      their sponsor receives the same amount as sponsor_income **only if sponsor.binary_eligible == True**.
    """

    today = timezone.now().date()
    income_binary = Decimal('0.00')
    income_flash = Decimal('0.00')
    sponsor_credit = Decimal('0.00')

    # compute totals (new joins today + carry-forwards)
    left_total = (member.left_new_today or 0) + (member.left_cf or 0)
    right_total = (member.right_new_today or 0) + (member.right_cf or 0)

    # ---------- ONE-TIME ELIGIBILITY CHECK ----------
    if not member.binary_eligible:
        # requirement: at least 1:2 or 2:1 to unlock (based on counts present now)
        if (left_total >= 1 and right_total >= 2) or (left_total >= 2 and right_total >= 1):
            # One-time credit for initial achievement: give 1 pair worth immediately
            # (As per spec: when they pass, they get 1 pair immediately)
            income_binary += PAIR_AMOUNT

            member.binary_eligible = True
            member.binary_eligible_date = timezone.now()
            # After giving initial achievement pair, reduce counts by 1 pair (1 left + 1 right)
            # But be careful: only reduce if both sides have at least 1.
            if left_total >= 1 and right_total >= 1:
                left_total -= 1
                right_total -= 1

            member.save(update_fields=['binary_eligible', 'binary_eligible_date'])

    # ---------- DAILY BINARY PAIR PAYMENT ----------
    if member.binary_eligible:
        matched_pairs_total = min(left_total, right_total)

        # Payable binary pairs (respect daily cap)
        payable_pairs = min(matched_pairs_total, DAILY_MAX_PAIRS)
        income_binary += Decimal(payable_pairs) * PAIR_AMOUNT

        # reduce matched pairs used for binary payment
        left_total -= payable_pairs
        right_total -= payable_pairs

    # ---------- FLASHOUT (repurchase) ----------
    # matched pairs left after binary payment -> form flash units (groups of 5 pairs)
    matched_pairs_after_binary = min(left_total, right_total)
    flash_units = matched_pairs_after_binary // FLASH_UNIT_PAIR

    if flash_units > 0:
        # cap daily flash units
        usable_units = min(flash_units, FLASH_UNIT_DAILY_MAX)
        income_flash = Decimal(usable_units) * FLASH_UNIT_VALUE

        # apply flash unit consumption from both sides
        consumed_pairs_for_flash = usable_units * FLASH_UNIT_PAIR
        left_total -= consumed_pairs_for_flash
        right_total -= consumed_pairs_for_flash

        # Excess units beyond daily cap are washout (ignored)
    else:
        usable_units = 0

    # ---------- CARRY FORWARD (unmatched members stay on their side) ----------
    # left_total and right_total now represent remaining unmatched members after binary+flash consumption
    # These are carried forward to next day as integer counts.
    # NOTE: these should be integers (counts of members), ensure no negatives.
    new_left_cf = max(int(left_total), 0)
    new_right_cf = max(int(right_total), 0)

    # ---------- PERSISTENT ACCOUNT UPDATES ----------
    # Update member carry-forward counters and binary_income field
    if income_binary > 0:
        # Add to member's binary_income total field
        member.binary_income = (member.binary_income or Decimal('0.00')) + income_binary

    # credit flash to repurchase_wallet (repurchase only - not cash)
    if income_flash > 0:
        member.repurchase_wallet = (member.repurchase_wallet or Decimal('0.00')) + income_flash

    # update carry forwards
    member.left_cf = new_left_cf
    member.right_cf = new_right_cf

    # Reset today's new counters after processing (since we've consumed them)
    member.left_new_today = 0
    member.right_new_today = 0

    # Save member changes
    member.save(update_fields=[
        'binary_income', 'repurchase_wallet', 'left_cf', 'right_cf',
        'left_new_today', 'right_new_today'
    ])

    # ---------- DAILY REPORT ----------
    # record binary + flash into DailyIncomeReport for this member
    _add_daily_report(member, today, binary=income_binary, flash=income_flash)

    # ---------- SPONSOR CREDIT ----------
    # Credit sponsor same amount as binary_income (only binary part) if sponsor eligible
    if income_binary > 0:
        sponsor_credit = _credit_sponsor_for_binary(member, income_binary, today)

    # Return a breakdown (Decimal amounts)
    return {
        'binary_income': income_binary,
        'flashout_income': income_flash,
        'sponsor_income_credit': sponsor_credit,
        'left_cf': member.left_cf,
        'right_cf': member.right_cf,
        'binary_eligible': member.binary_eligible,
        'flash_units_used': usable_units if 'usable_units' in locals() else 0,
    }

