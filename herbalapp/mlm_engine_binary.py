# mlm_engine_binary.py
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class IncomeContext:
    member_id: int
    date: str

    # Today new joins on each side
    today_left_joins: int = 0
    today_right_joins: int = 0

    # Carry forward BEFORE today
    left_cf_before: int = 0
    right_cf_before: int = 0

    # Total BV (repurchase) for each side (PRESERVED but NOT used for eligibility)
    total_left_bv: int = 0
    total_right_bv: int = 0

    # Binary eligibility (one-time)
    binary_eligible: bool = False

    # Stock commission inputs (not used fully, because branch based)
    stock_role: str | None = None
    stock_billing: int = 0

    # Results (filled by engine)
    left_cf_after: int = 0
    right_cf_after: int = 0
    binary_pairs_paid: int = 0
    binary_income: Decimal = Decimal("0.00")
    flash_income: Decimal = Decimal("0.00")
    salary_income: Decimal = Decimal("0.00")
    stock_commission: Decimal = Decimal("0.00")
    rank_title: str | None = None


# -----------------------------
# CONFIG
# -----------------------------
BINARY_PAIR_AMOUNT = Decimal("500.00")  # Rs 500 per pair
FLASHOUT_LIMIT = Decimal("5000.00")
FLASHOUT_PERCENT = Decimal("0.50")
SALARY_PERCENT = Decimal("0.05")  # 5% of matched BV


# -----------------------------
# COUNT-BASED ELIGIBILITY
# -----------------------------
def check_binary_eligibility(ctx: IncomeContext) -> bool:
    """
    One-time eligibility based on MEMBER COUNT:
    - 1:2 or 2:1
    BV is preserved but NOT used for eligibility.
    """
    left_total = ctx.left_cf_before + ctx.today_left_joins
    right_total = ctx.right_cf_before + ctx.today_right_joins

    cond_1_2 = (left_total >= 1 and right_total >= 2)
    cond_2_1 = (left_total >= 2 and right_total >= 1)

    return cond_1_2 or cond_2_1


# -----------------------------
# MAIN ENGINE (COUNT-BASED)
# -----------------------------
def process_daily_income(ctx: IncomeContext, direct_binary_incomes=None) -> IncomeContext:
    """
    Core binary + flash + salary + rank + stock engine.
    COUNT-BASED eligibility (1:2 or 2:1).
    BV is preserved but NOT used for eligibility.
    """

    # 1) One-time eligibility
    if not ctx.binary_eligible:
        ctx.binary_eligible = check_binary_eligibility(ctx)

    # 2) TOTAL available joins including CF
    left_total = ctx.left_cf_before + ctx.today_left_joins
    right_total = ctx.right_cf_before + ctx.today_right_joins

    # 3) PAIRS possible today
    pairs = min(left_total, right_total)

    # 4) Carry forward AFTER using pairs
    ctx.left_cf_after = left_total - pairs
    ctx.right_cf_after = right_total - pairs

    # 5) Binary income (count-based)
    if ctx.binary_eligible and pairs > 0:
        gross_binary = BINARY_PAIR_AMOUNT * pairs
    else:
        gross_binary = Decimal("0.00")

    ctx.binary_pairs_paid = pairs
    ctx.binary_income = gross_binary

    # 6) Flashout
    flash_income = Decimal("0.00")
    final_binary = gross_binary

    if gross_binary > FLASHOUT_LIMIT:
        excess = gross_binary - FLASHOUT_LIMIT
        flash_income = excess * FLASHOUT_PERCENT
        final_binary = gross_binary - flash_income

    ctx.flash_income = flash_income
    ctx.binary_income = final_binary

    # 7) Salary income (BV-based, preserved)
    matched_bv = min(ctx.total_left_bv, ctx.total_right_bv)
    ctx.salary_income = (Decimal(matched_bv) * SALARY_PERCENT).quantize(Decimal("1.00"))

    # 8) Stock commission (branch-based, disabled)
    ctx.stock_commission = Decimal("0.00")

    # 9) Rank logic (BV-based, preserved)
    ctx.rank_title = determine_rank_from_bv(matched_bv)

    return ctx


# -----------------------------
# RANK LOGIC (BV-based)
# -----------------------------
def determine_rank_from_bv(matched_bv: int) -> str | None:
    """
    Rank titles based on matched BV (Left = Right).
    BV logic preserved for future use.
    """
    bv = matched_bv

    if bv >= 250000000:
        return "Triple Diamond"
    elif bv >= 100000000:
        return "Double Diamond"
    elif bv >= 50000000:
        return "Diamond Star"
    elif bv >= 25000000:
        return "Mono Platinum Star"
    elif bv >= 10000000:
        return "Platinum Star"
    elif bv >= 5000000:
        return "Gilded Gold"
    elif bv >= 2500000:
        return "Gold Star"
    elif bv >= 1000000:
        return "Shine Silver (Advanced)"
    elif bv >= 500000:
        return "Shine Silver"
    elif bv >= 250000:
        return "Triple Star / Silver Star"
    elif bv >= 100000:
        return "Double Star"
    elif bv >= 50000:
        return "1st Star"

    return None

