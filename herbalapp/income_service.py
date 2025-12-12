# herbalapp/income_service.py

from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from herbalapp.models import Member, DailyIncomeReport
from herbalapp.mlm_engine_binary import IncomeContext, process_daily_income


# =========================
# BASIC HELPERS
# =========================

def _get_today():
    return timezone.now().date()


def build_income_context_for_member(member: Member) -> IncomeContext:
    """
    Build IncomeContext for the placement parent (upline)
    based on today's joins + current CF + BV.

    IMPORTANT:
    - Eligibility is now COUNT-BASED (1:2 or 2:1).
    - BV is preserved only for salary/rank, not eligibility.
    """

    # Today’s new joins on each side (count only, NOT BV)
    today_left_joins = member.left_new_today or 0
    today_right_joins = member.right_new_today or 0

    # Carry-forward counts
    left_cf_before = member.left_cf or 0
    right_cf_before = member.right_cf or 0

    # BV totals (repurchase only) using existing helper
    bv_data = member.calculate_bv()
    total_left_bv = int(bv_data.get("left_bv", 0))
    total_right_bv = int(bv_data.get("right_bv", 0))

    ctx = IncomeContext(
        member_id=member.id,
        date=_get_today().isoformat(),
        today_left_joins=today_left_joins,
        today_right_joins=today_right_joins,
        left_cf_before=left_cf_before,
        right_cf_before=right_cf_before,
        total_left_bv=total_left_bv,
        total_right_bv=total_right_bv,
        binary_eligible=member.binary_eligible,
        stock_role=None,
        stock_billing=0,
    )
    return ctx


def update_member_from_context(member: Member, ctx: IncomeContext):
    """
    Take the calculated engine context and write values back to Member model.
    Also update wallets. This is ONLY for the placement parent.
    """

    # Carry forward
    member.left_cf = ctx.left_cf_after
    member.right_cf = ctx.right_cf_after

    # Binary income
    member.binary_pairs += ctx.binary_pairs_paid
    member.binary_income += Decimal(ctx.binary_income)

    # Wallet updates – main wallet gets binary + salary (and optionally flash/stock if you want)
    member.main_wallet += Decimal(ctx.binary_income)

    # Flash income
    member.flash_wallet += Decimal(ctx.flash_income)
    member.flash_bonus += Decimal(ctx.flash_income)

    # Salary (BV-based)
    member.salary += Decimal(ctx.salary_income)
    member.main_wallet += Decimal(ctx.salary_income)

    # Rank (update title if changed)
    if ctx.rank_title and ctx.rank_title != (member.current_rank or ""):
        member.current_rank = ctx.rank_title
        member.rank_assigned_at = timezone.now()

    # Stock commission (OPTIONAL: if you still credit some member-level stock commission)
    member.stock_commission += Decimal(ctx.stock_commission)
    member.main_wallet += Decimal(ctx.stock_commission)

    # IMPORTANT: mark member as eligible permanently once reached
    if ctx.binary_eligible and not member.binary_eligible:
        member.binary_eligible = True

    member.save()


def log_daily_income(member: Member, ctx: IncomeContext, sponsor_income: Decimal = Decimal("0.00")):
    """
    Create or update a DailyIncomeReport row for this member for today.
    If a row exists, we add to it; otherwise we create a new one.
    """
    today = _get_today()

    report, created = DailyIncomeReport.objects.get_or_create(
        member=member,
        date=today,
        defaults={
            "binary_income": Decimal("0.00"),
            "flash_bonus": Decimal("0.00"),
            "sponsor_income": Decimal("0.00"),
            "salary": Decimal("0.00"),
            "stock_commission": Decimal("0.00"),
            "total_income": Decimal("0.00"),
        },
    )

    report.binary_income += Decimal(ctx.binary_income)
    report.flash_bonus += Decimal(ctx.flash_income)
    report.salary += Decimal(ctx.salary_income)
    report.stock_commission += Decimal(ctx.stock_commission)
    report.sponsor_income += Decimal(sponsor_income)

    report.total_income = (
        report.binary_income
        + report.flash_bonus
        + report.sponsor_income
        + report.salary
        + report.stock_commission
    )

    report.save()


# =========================
# SPONSOR LOGIC (FINAL)
# =========================

def apply_sponsor_income_for_new_join(new_member: Member, ctx: IncomeContext) -> Decimal:
    """
    Sponsor income logic for NEW JOIN only.

    CASE 1 — Placement ID = Sponsor ID:
        - Sponsor income goes to placement_parent.sponsor

    CASE 2 — Placement ID != Sponsor ID:
        - Sponsor income goes to Sponsor ID directly
    """

    placement_parent = new_member.placement
    sponsor_member = new_member.sponsor

    # No sponsor logic possible if both missing
    if not placement_parent and not sponsor_member:
        return Decimal("0.00")

    # CASE 1: Placement and Sponsor same person
    if placement_parent and sponsor_member and placement_parent == sponsor_member:
        final_sponsor = placement_parent.sponsor
    else:
        # CASE 2: Sponsor is different → sponsor id gets it directly
        final_sponsor = sponsor_member

    if not final_sponsor:
        return Decimal("0.00")

    sponsor_income_amount = Decimal(ctx.binary_income)

    final_sponsor.sponsor_income += sponsor_income_amount
    final_sponsor.main_wallet += sponsor_income_amount
    final_sponsor.save()

    # Log sponsor income in DailyIncomeReport for the sponsor
    today = _get_today()
    sponsor_report, created = DailyIncomeReport.objects.get_or_create(
        member=final_sponsor,
        date=today,
        defaults={
            "binary_income": Decimal("0.00"),
            "flash_bonus": Decimal("0.00"),
            "sponsor_income": Decimal("0.00"),
            "salary": Decimal("0.00"),
            "stock_commission": Decimal("0.00"),
            "total_income": Decimal("0.00"),
        },
    )
    sponsor_report.sponsor_income += sponsor_income_amount
    sponsor_report.total_income += sponsor_income_amount
    sponsor_report.save()

    return sponsor_income_amount


# =========================
# MAIN: NEW JOIN INTEGRATION
# =========================

@transaction.atomic
def run_binary_on_new_join(new_member: Member):
    """
    Main integration: call this AFTER a new member is saved.

    - Updates placement parent's join counts for today
    - Builds IncomeContext for placement parent
    - Runs binary + CF + flashout + salary + rank + stock (from engine)
    - Applies sponsor income using CASE1/CASE2 rule
    - Updates placement parent model + wallets
    - Logs DailyIncomeReport for placement parent and sponsor
    """

    placement_parent = new_member.placement

    # If no placement parent, no binary impact
    if not placement_parent:
        return None

    # Update today's join counters for placement parent
    if new_member.side == "left":
        placement_parent.left_join_count += 1
        placement_parent.left_new_today += 1
    elif new_member.side == "right":
        placement_parent.right_join_count += 1
        placement_parent.right_new_today += 1

    placement_parent.save()

    # Build engine context for placement parent
    ctx = build_income_context_for_member(placement_parent)

    # Run the ENGINE (now COUNT-BASED via updated mlm_engine_binary)
    ctx = process_daily_income(ctx, direct_binary_incomes=None)

    # Apply sponsor income rule
    sponsor_income_amount = apply_sponsor_income_for_new_join(new_member, ctx)

    # Update placement parent from context (binary, CF, salary, stock, wallets, eligibility)
    update_member_from_context(placement_parent, ctx)

    # Log placement parent's daily income including binary/flash/salary/stock
    log_daily_income(placement_parent, ctx)

    return {
        "placement_parent": placement_parent,
        "ctx": ctx,
        "sponsor_income": sponsor_income_amount,
    }

