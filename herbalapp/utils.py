# herbalapp/utils.py

from .models import Member, Commission

# ----------------------------------------------------
# ✅ Sponsor Check-Match Income (DISABLED for new engine)
# ----------------------------------------------------
# New MLM engine handles sponsor income ONLY when
# a child becomes eligible (1:2 or 2:1).
# Sponsor income is created in:
#   run_binary_engine_for_day() → SponsorIncome.objects.create()
#
# This function is kept ONLY for backward compatibility.
# It now returns 0 to avoid double income.

def calculate_sponsor_income(member):
    return 0


# ----------------------------------------------------
# ✅ District / Taluk / Pincode Commission (unchanged)
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
# ✅ Auto-ID Generator (unchanged)
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

