# herbalapp/utils.py

from .models import Member, Commission

# ----------------------------------------------------
# ✅ Sponsor Check-Match Income (still valid)
# ----------------------------------------------------
def calculate_sponsor_income(member):
    sponsor_income = 0
    directs = member.sponsored_members.all()

    for d in directs:
        latest_income = d.incomes.order_by("-id").first()
        if latest_income:
            sponsor_income += latest_income.binary_income

    return sponsor_income


# ----------------------------------------------------
# ✅ District / Taluk / Pincode Commission
# ----------------------------------------------------
def calculate_commission(payment):
    member = payment.member
    amount = payment.amount

    commissions = []

    # District level commission (7%)
    if member.district:
        commissions.append(('district', 7, amount * 0.07))

    # Taluk level commission (5%)
    if member.taluk:
        commissions.append(('taluk', 5, amount * 0.05))

    # Pincode level commission (3%)
    if member.pincode:
        commissions.append(('pincode', 3, amount * 0.03))

    # Save commissions
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

