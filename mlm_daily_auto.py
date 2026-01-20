#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import django
import subprocess
from datetime import date

# ✅ Correct Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rocky_herbals2.settings")
django.setup()

from herbalapp.models import Member, DailyIncomeReport

ROOT_ID = "rocky004"   # Dummy/root member
today = date.today()    # Or set specific date

# ----------------------------
# Step 1: Reset dummy/root incomes
# ----------------------------
DailyIncomeReport.objects.filter(member__auto_id=ROOT_ID).update(
    binary_income=0,
    binary_eligibility_income=0,
    sponsor_income=0,
    flashout_wallet_income=0,
    total_income=0
)

# ----------------------------
# Step 2: Recalculate left/right counts dynamically
# ----------------------------
def recalc_counts(member):
    left_total = 0
    right_total = 0

    left_children = Member.objects.filter(parent=member, side="left").exclude(auto_id=ROOT_ID)
    right_children = Member.objects.filter(parent=member, side="right").exclude(auto_id=ROOT_ID)

    left_total += left_children.count()
    right_total += right_children.count()

    for child in left_children:
        l, r = recalc_counts(child)
        left_total += l + r

    for child in right_children:
        l, r = recalc_counts(child)
        right_total += l + r

    # Update carry_forward counts
    member.left_carry_forward = left_total
    member.right_carry_forward = right_total
    member.save(update_fields=["left_carry_forward", "right_carry_forward"])

    return left_total, right_total

# ----------------------------
# Step 3: Apply to all members except ROOT_ID
# ----------------------------
members = Member.objects.exclude(auto_id=ROOT_ID)
for m in members:
    recalc_counts(m)

print("✅ Left/Right counts recalculated for all members excluding root/dummy.")

# ----------------------------
# Step 4: Run MLM daily engine
# ----------------------------
subprocess.run([
    "/home/senthiltex007/rocky_sri_herbals/venv/bin/python",
    "/home/senthiltex007/rocky_sri_herbals/manage.py",
    "mlm_run_daily",
    "--date", str(today)
])

print("✅ MLM engine run completed with updated counts.")

