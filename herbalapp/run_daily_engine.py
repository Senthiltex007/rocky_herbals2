# herbalapp/run_daily_engine.py
import sys, os
from datetime import date
from django.utils import timezone

PROJECT_ROOT = "/home/senthiltex007/rocky_sri_herbals"
sys.path.insert(0, PROJECT_ROOT)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rocky_herbals2.settings")
django.setup()

from herbalapp.models import Member, SponsorIncome

# -------------------------------
# Constants
# -------------------------------
PAIR_VALUE = 500
SPONSOR_RATE = 500
FLASHOUT_UNIT_VALUE = 1000
DAILY_BINARY_PAIR_LIMIT = 5
MAX_FLASHOUT_UNITS = 9

run_date = date(2025, 12, 19)
print("✅ Running Daily Income Report with Binary, Sponsor, Flashout, Washout Rules for:", run_date)

members = Member.objects.all()

for member in members:
    # -------------------------------
    # Count left/right joins today + carry forward
    # -------------------------------
    left_today = Member.objects.filter(placement=member, position="left", joined_date=run_date).count()
    right_today = Member.objects.filter(placement=member, position="right", joined_date=run_date).count()

    left_cf_before = getattr(member, "left_cf", 0)
    right_cf_before = getattr(member, "right_cf", 0)

    L = left_today + left_cf_before
    R = right_today + right_cf_before

    # ✅ Total pairs today
    pairs_today = min(L, R)

    # -------------------------------
    # Binary income (first 5 pairs)
    # -------------------------------
    binary_pairs = min(pairs_today, DAILY_BINARY_PAIR_LIMIT)
    binary_income = binary_pairs * PAIR_VALUE

    # -------------------------------
    # Flashout income (next groups of 5 pairs)
    # -------------------------------
    leftover_pairs = pairs_today - binary_pairs
    flashout_units = min(leftover_pairs // 5, MAX_FLASHOUT_UNITS)
    flashout_income = flashout_units * FLASHOUT_UNIT_VALUE

    # -------------------------------
    # Washout pairs (beyond binary + flashout cap)
    # -------------------------------
    washout_pairs = leftover_pairs - (flashout_units * 5)
    if washout_pairs < 0:
        washout_pairs = 0

    # ✅ Carry forward = only unpaired members, not washout
    L -= pairs_today
    R -= pairs_today
    member.left_cf = L
    member.right_cf = R
    member.save()

    # -------------------------------
    # Sponsor income (mirrors binary pairs only)
    # -------------------------------
    sponsor_receiver = None
    sponsor_income = 0
    if member.sponsor and binary_pairs > 0:
        if member.sponsor == member.placement:
            if member.placement and member.placement.sponsor:
                sponsor_receiver = member.placement.sponsor
            else:
                sponsor_receiver = member.sponsor
        else:
            sponsor_receiver = member.sponsor

        if sponsor_receiver:
            sponsor_income = min(binary_pairs, 5) * SPONSOR_RATE
            SponsorIncome.objects.get_or_create(
                sponsor=sponsor_receiver,
                child=member,
                date=run_date,
                defaults={"amount": sponsor_income}
            )
            print(f"✅ Sponsor income {sponsor_income} → receiver={sponsor_receiver.member_id} from child={member.member_id}")

    # -------------------------------
    # Totals
    # -------------------------------
    total_direct_income = binary_income + sponsor_income
    repurchase_wallet_income = flashout_income

    # -------------------------------
    # Print report
    # -------------------------------
    print({
        "member_id": member.member_id,
        "name": member.name,
        "pairs_today": pairs_today,
        "binary_income": binary_income,
        "sponsor_income": sponsor_income,
        "flashout_units": flashout_units,
        "flashout_income_repurchase_wallet": repurchase_wallet_income,
        "washout_pairs": washout_pairs,
        "carry_forward_left": member.left_cf,
        "carry_forward_right": member.right_cf,
        "total_direct_income": total_direct_income,
        "repurchase_wallet": repurchase_wallet_income,
    })

print("✅ Daily Income Report Completed with Binary, Sponsor, Flashout, Washout Rules")

