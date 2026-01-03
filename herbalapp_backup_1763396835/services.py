# herbalapp/services.py
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Member

@transaction.atomic
def place_member(child: Member, parent: Member, side: str, sponsor: Member | None = None):
    side = side.upper()
    if side not in ('L', 'R'):
        raise ValidationError("Side must be 'L' or 'R'.")

    if child.parent is not None:
        raise ValidationError("Member is already placed under a parent.")

    # Ensure parent has free slot
    if side == 'L':
        if parent.left_child is not None:
            raise ValidationError("Parent already has a left child.")
        parent.left_child = child
    else:
        if parent.right_child is not None:
            raise ValidationError("Parent already has a right child.")
        parent.right_child = child

    # Set child links
    child.parent = parent
    child.position = side
    if sponsor:
        child.sponsor = sponsor

    # Save in safe order
    parent.save(update_fields=['left_child', 'right_child'])
    child.save(update_fields=['parent', 'position', 'sponsor'])
    return child

