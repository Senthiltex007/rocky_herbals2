from django.db import transaction
from herbalapp.models import Member
from .auto_id import generate_auto_id

def create_member(**kwargs):
    """
    Create a new Member safely with auto_id and default fields.
    """
    with transaction.atomic():
        member = Member(**kwargs)

        # Auto ID
        if not member.auto_id:
            member.auto_id = generate_auto_id()

        # Default fields
        member.left_cf = 0
        member.right_cf = 0
        member.binary_income = 0
        member.repurchase_wallet = 0
        member.binary_eligible = False
        member.binary_eligible_date = None

        member.save()
        return member

