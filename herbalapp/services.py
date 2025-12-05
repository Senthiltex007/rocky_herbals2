from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from .models import Member, RankReward, Income, IncomeRecord, CommissionRecord
from .ranks import RANKS


# -------------------------------------------------------------
#  RANK ASSIGNMENT
# -------------------------------------------------------------
def assign_rank_if_eligible(member: Member):
    left_bv, right_bv = member.get_bv_counts()
    matched_bv = min(left_bv, right_bv)

    for cfg in RANKS:
        if matched_bv >= int(cfg["min_matched_bv"]):
            exists = RankReward.objects.filter(
                member=member,
                rank_title=cfg["title"],
                active=True
            ).exists()
            if exists:
                return None

            reward = RankReward.objects.create(
                member=member,
                rank_title=cfg["title"],
                left_bv_snapshot=left_bv,
                right_bv_snapshot=right_bv,
                monthly_income=int(cfg["monthly"]),
                duration_months=int(cfg["months"]),
                start_date=timezone.now().date(),
                months_paid=0,
                active=True,
            )

            member.current_rank = cfg["title"]
            member.rank_assigned_at = timezone.now()
            member.save(update_fields=["current_rank", "rank_assigned_at"])
            return reward

    return None


# -------------------------------------------------------------
#  PLACE MEMBER UNDER A PARENT
# -------------------------------------------------------------
@transaction.atomic
def place_member(child: Member, parent: Member, side: str, sponsor: Member | None = None):
    side = side.lower()
    if side not in ('left', 'right'):
        raise ValidationError("Side must be 'left' or 'right'.")

    if child.parent is not None:
        raise ValidationError("Member is already placed under a parent.")

    if side == 'left':
        if parent.left_child is not None:
            raise ValidationError("Parent already has a left child.")
        parent.left_child = child
    else:
        if parent.right_child is not None:
            raise ValidationError("Parent already has a right child.")
        parent.right_child = child

    child.parent = parent
    child.side = side
    if sponsor:
        child.sponsor = sponsor

    parent.save(update_fields=['left_child', 'right_child'])
    child.save(update_fields=['parent', 'side', 'sponsor'])
    return child


# ==========================================================================================
# 🔥 NEW BINARY INCOME SYSTEM (ONE-TIME ELIGIBILITY + DAILY BINARY)
# ==========================================================================================

# -------------------------------------------------------------
#  ONE-TIME ELIGIBILITY CHECK (1:2 or 2:1)
# -------------------------------------------------------------
def check_binary_eligibility(member):
    """
    Binary eligibility only ONE TIME.
    Need 1:2 or 2:1 structure to unlock income.
    """
    left = member.left_join_count
    right = member.right_join_count

    if member.binary_eligible:
        return True

    # Rule 1: 1 left, 2 right
    if left >= 1 and right >= 2:
        member.binary_eligible = True
        member.binary_eligible_date = timezone.now()
        member.save(update_fields=['binary_eligible', 'binary_eligible_date'])
        return True

    # Rule 2: 2 left, 1 right
    if left >= 2 and right >= 1:
        member.binary_eligible = True
        member.binary_eligible_date = timezone.now()
        member.save(update_fields=['binary_eligible', 'binary_eligible_date'])
        return True

    return False


# -------------------------------------------------------------
#  DAILY BINARY INCOME (AFTER ELIGIBILITY)
# -------------------------------------------------------------
def calculate_daily_binary(member, left_new, right_new):
    """
    Daily binary income:
    - Only after eligibility unlock
    - 1 pair = ₹500
    - Max 5 pairs/day
    - Extra carried forward
    """

    if not member.binary_eligible:
        return 0

    left_total = member.left_cf + left_new
    right_total = member.right_cf + right_new

    # Today's matched pairs
    pairs_today = min(left_total, right_total)
    payable_pairs = min(pairs_today, 5)
    income_amount = payable_pairs * 500

    # Save income
    if income_amount > 0:
        IncomeRecord.objects.create(
            member=member,
            amount=income_amount,
            type="Binary Income (Daily)"
        )

    # Update carry forward
    member.left_cf = left_total - payable_pairs
    member.right_cf = right_total - payable_pairs
    member.save(update_fields=['left_cf', 'right_cf'])

    return income_amount


# -------------------------------------------------------------
#  RUN AFTER NEW MEMBER JOINS UNDER SOMEONE
# -------------------------------------------------------------
def process_after_member_join(parent):
    """
    After a member joins:
    - Update left/right join counts
    - Check eligibility
    - If eligible, calculate binary income
    """

    # Update join counts
    parent.left_join_count = parent.left_child.total_count() if parent.left_child else 0
    parent.right_join_count = parent.right_child.total_count() if parent.right_child else 0
    parent.save(update_fields=['left_join_count', 'right_join_count'])

    # Eligibility
    eligible = check_binary_eligibility(parent)

    # Daily calculation
    if eligible:
        income = calculate_daily_binary(
            parent,
            parent.left_new_today,
            parent.right_new_today
        )
        return income

    return 0


# -------------------------------------------------------------
#  SALARY INCOME BASED ON MATCHED BV
# -------------------------------------------------------------
def add_salary_income(member: Member, bv_a: int, bv_b: int):
    matched_bv = min(bv_a, bv_b)
    amount = 0
    if matched_bv >= 250000:
        amount = 10000
    elif matched_bv >= 100000:
        amount = 5000
    elif matched_bv >= 50000:
        amount = 3000

    if amount:
        today = timezone.now().date()
        income_row, _ = Income.objects.get_or_create(member=member, date=today)
        income_row.salary_income += amount
        income_row.save()
        IncomeRecord.objects.create(member=member, amount=amount, type=f"Salary BV Match ({matched_bv})")

    return amount


# -------------------------------------------------------------
#  ENRICH MEMBER SUMMARY
# -------------------------------------------------------------
def enrich_member(member):
    member.left_count = 1 if member.left_child else 0
    member.right_count = 1 if member.right_child else 0
    try:
        member.total_income = sum(i.amount for i in member.income_set.all())
    except Exception:
        member.total_income = 0
    return member


# -------------------------------------------------------------
#  BILLING COMMISSION (80% repurchase + 20% flash)
# -------------------------------------------------------------
def add_billing_commission(member: Member, amount: int, level: str = "direct"):

    rep_amount = amount * Decimal("0.80")
    flash_amount = amount * Decimal("0.20")

    CommissionRecord.objects.create(
        member=member,
        amount=amount,
        level=level,
        created_at=timezone.now()
    )

    member.repurchase_wallet += rep_amount
    member.flash_wallet += flash_amount
    member.save(update_fields=["repurchase_wallet", "flash_wallet"])

    return amount

