# herbalapp/utils.py
from .models import Income, Member

# -------------------------------
# Binary Income Calculation
# -------------------------------
def calculate_binary_income(left_pairs, right_pairs):
    matched_pairs = min(left_pairs, right_pairs)
    ceiling_pairs = min(matched_pairs, 5)  # daily ceiling
    binary_income = ceiling_pairs * 500

    # Flash Out Bonus
    flash_out_bonus = 0
    if matched_pairs > 5:
        extra_pairs = matched_pairs - 5
        flash_units = min(extra_pairs // 5, 5)  # max 5 units
        flash_out_bonus = flash_units * 1000

    return binary_income, flash_out_bonus, matched_pairs


# -------------------------------
# Sponsor Check Match Income
# -------------------------------
def calculate_sponsor_income(member):
    sponsor_income = 0
    directs = member.sponsored_members.all()
    for d in directs:
        latest_income = Income.objects.filter(member=d).last()
        if latest_income:
            sponsor_income += latest_income.binary_income
    return sponsor_income


# -------------------------------
# Salary Income (BV Matching)
# -------------------------------
def calculate_salary_income(bv_left, bv_right):
    salary_income = 0
    matched_bv = min(bv_left, bv_right)

    if matched_bv >= 50000:
        salary_income += 3000 * 3
    if matched_bv >= 10000:
        salary_income += 5000 * 4
    if matched_bv >= 250000:
        salary_income += 10000 * 5

    return salary_income


# -------------------------------
# Generate Income Record
# -------------------------------
def generate_income(member, left_pairs, right_pairs, bv_left, bv_right):
    binary_income, flash_out_bonus, matched_pairs = calculate_binary_income(left_pairs, right_pairs)
    sponsor_income = calculate_sponsor_income(member)
    salary_income = calculate_salary_income(bv_left, bv_right)

    Income.objects.create(
        member=member,
        binary_pairs=matched_pairs,
        binary_income=binary_income,
        sponsor_income=sponsor_income,
        flash_out_bonus=flash_out_bonus,
        salary_income=salary_income
    )
    return binary_income + sponsor_income + flash_out_bonus + salary_income

# herbalapp/utils.py
from .models import Commission

def calculate_commission(payment):
    member = payment.member
    amount = payment.amount

    commissions = []

    # District level commission (7%)
    if member.district:
        commission_amount = amount * 0.07
        commissions.append(('district', 7, commission_amount))

    # Taluk level commission (5%)
    if member.taluk:
        commission_amount = amount * 0.05
        commissions.append(('taluk', 5, commission_amount))

    # Pincode level commission (3%)
    if member.pincode:
        commission_amount = amount * 0.03
        commissions.append(('pincode', 3, commission_amount))

    # Save commissions
    for ctype, perc, camount in commissions:
        Commission.objects.create(
            member=member,
            payment=payment,
            commission_type=ctype,
            percentage=perc,
            commission_amount=camount
        )

# -------------------------------
# Sequential Auto-ID Generator
# -------------------------------
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

