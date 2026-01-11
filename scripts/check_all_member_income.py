#!/usr/bin/env python
"""
Check all member daily income for a given date.
Run with Django shell:
    python manage.py runscript check_all_member_income
"""

from decimal import Decimal
from herbalapp.models import DailyIncomeReport

# ✅ Change this to the date you want to check
run_date = "2026-01-08"

# Get all income reports for that date
reports = DailyIncomeReport.objects.filter(date=run_date).select_related("member")

if not reports.exists():
    print(f"❌ No income reports found for {run_date}")
else:
    print(f"💰 MLM Daily Income Reports for {run_date}\n")
    print(f"{'Auto ID':<10} | {'Binary':<10} | {'Sponsor':<10} | {'Flashout':<10} | {'Total':<10}")
    print("-" * 60)

    for r in reports:
        binary = Decimal(r.binary_income)
        sponsor = Decimal(r.sponsor_income)
        flashout = getattr(r, 'flashout_units', 0)
        total = Decimal(r.total_income)
        print(f"{r.member.auto_id:<10} | {binary:<10} | {sponsor:<10} | {flashout:<10} | {total:<10}")

    print(f"\n✅ Total members: {reports.count()}")

