# ==========================================================
# herbalapp/utils/member_creator.py (FINAL CLEAN VERSION)
# ==========================================================
from django.db import transaction
from herbalapp.models import Member

def create_member(**kwargs):
    """
    Create a new Member safely with manual member_id and default fields.
    """
    with transaction.atomic():
        member = Member(**kwargs)

        # ✅ Manual member_id must be provided in kwargs
        if not member.member_id:
            raise ValueError("member_id is required for creating a Member")

        # Default fields
        member.left_cf = 0
        member.right_cf = 0
        member.binary_income = 0
        member.repurchase_wallet = 0
        member.binary_eligible = False
        member.binary_eligible_date = None

        member.save()
        return member

