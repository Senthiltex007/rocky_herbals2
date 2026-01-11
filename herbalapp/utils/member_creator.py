# herbalapp/utils/member_creator.py

from django.db import transaction
from herbalapp.models import Member
from .auto_id import generate_auto_id


def create_member(
    *,
    name,
    sponsor,
    parent,
    position,   # "left" or "right"
    **extra_fields
):
    """
    Create a new MLM Member with proper tree + sponsor updates
    """

    if position not in ("left", "right"):
        raise ValueError("position must be 'left' or 'right'")

    with transaction.atomic():

        # -----------------------------
        # Create member
        # -----------------------------
        member = Member(
            name=name,
            sponsor=sponsor,
            parent=parent,
            position=position,
            **extra_fields
        )

        # Auto ID
        member.auto_id = generate_auto_id()

        # Default binary values
        member.left_cf = 0
        member.right_cf = 0
        member.binary_income = 0
        member.repurchase_wallet = 0
        member.binary_eligible = False
        member.binary_eligible_date = None

        member.save()

        # -----------------------------
        # Update parent join counts
        # -----------------------------
        if position == "left":
            parent.left_joins_today += 1
        else:
            parent.right_joins_today += 1

        parent.save(update_fields=[
            "left_joins_today",
            "right_joins_today"
        ])

        return member

