# herbalapp/utils.py
# ==================================================
# SAFE UTILS – NO MLM ENGINE LOGIC
# ==================================================

from decimal import Decimal
from .models import Member, Commission, DailyIncomeReport


# ----------------------------------------------------
# ✅ District / Taluk / Pincode Commission
# (Non-MLM, safe to keep)
# ----------------------------------------------------
def calculate_commission(payment):
    member = payment.member
    amount = payment.amount

    commissions = []

    if member.district:
        commissions.append(("district", 7, amount * Decimal("0.07")))

    if member.taluk:
        commissions.append(("taluk", 5, amount * Decimal("0.05")))

    if member.pincode:
        commissions.append(("pincode", 3, amount * Decimal("0.03")))

    for ctype, perc, camount in commissions:
        Commission.objects.create(
            member=member,
            payment=payment,
            commission_type=ctype,
            percentage=perc,
            commission_amount=camount
        )


# ----------------------------------------------------
# ✅ Auto-ID Generator
# ----------------------------------------------------
def generate_auto_id():
    last_member = Member.objects.order_by("-id").first()

    if last_member and last_member.auto_id.startswith("rocky"):
        try:
            num = int(last_member.auto_id.replace("rocky", ""))
        except ValueError:
            num = 0
        new_num = num + 1
    else:
        new_num = 1

    return f"rocky{new_num:04d}"


# ----------------------------------------------------
# ✅ DAILY TOTAL INCOME CALCULATOR (SAFE)
# ----------------------------------------------------
def calculate_daily_income(report: DailyIncomeReport):
    """
    SAFE TOTAL CALCULATOR (CASH TOTAL)

    ✅ Cash Total = eligibility + binary + sponsor + salary (if cash)
    ❌ Does NOT include flashout_wallet_income (repurchase-only wallet)
    - NO binary logic
    - NO sponsor logic
    - Just sums already-calculated cash fields
    """

    report.total_income = (
        (report.binary_eligibility_income or Decimal("0.00")) +
        (report.binary_income or Decimal("0.00")) +
        (report.sponsor_income or Decimal("0.00")) +
        (getattr(report, "salary_income", Decimal("0.00")) or Decimal("0.00"))
    )

    report.save(update_fields=["total_income"])
    return report.total_income

