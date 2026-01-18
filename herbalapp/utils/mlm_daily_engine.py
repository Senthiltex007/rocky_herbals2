# herbalapp/utils/mlm_daily_engine.py

from django.db import transaction
from herbalapp.models import Member
from herbalapp.mlm_engine_binary_runner import run_binary_engine
from herbalapp.mlm.sponsor_engine import run_sponsor_engine


@transaction.atomic
def run_daily_engine(run_date):
    """
    Daily MLM Engine – Order is VERY IMPORTANT

    Step 1: Binary + Eligibility
    Step 2: Sponsor Income (depends on step 1)
    """

    members = Member.objects.filter(is_active=True).order_by("id")

    # -------------------------------------------------
    # 1️⃣ Binary + Eligibility (STRICT 1:1 RULE INSIDE)
    # -------------------------------------------------
    for member in members:
        run_binary_engine(member, run_date)

    # -------------------------------------------------
    # 2️⃣ Sponsor Income (only from valid child income)
    # -------------------------------------------------
    for member in members:
        run_sponsor_engine(member, run_date)

