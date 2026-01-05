# mlm_tree_dynamic.py
#
# Rule-based MLM tree generator (parent + side)
# SAFE for your current Member model
#
# Run:
# python manage.py shell -c "exec(open('mlm_tree_dynamic.py').read())"

from herbalapp.models import Member
from django.db import transaction


def create_member(name, parent=None, side=None):
    """
    Create member with MLM structure
    """
    return Member.objects.create(
        name=name,
        parent=parent,
        side=side
    )


def build_mlm_tree(levels=3, root_name="ROOT"):
    """
    Builds MLM tree using:
    - parent
    - side (left / right)
    """

    if levels < 1:
        raise ValueError("levels must be >= 1")

    # -----------------------
    # Root
    # -----------------------
    root = create_member(root_name)
    current_level = [root]
    counter = 1

    # -----------------------
    # Level-wise build
    # -----------------------
    for lvl in range(1, levels):
        next_level = []

        for parent in current_level:
            # LEFT
            left = create_member(
                name=f"M_L{lvl}_{counter}",
                parent=parent,
                side="left"
            )
            counter += 1

            # RIGHT
            right = create_member(
                name=f"M_L{lvl}_{counter}",
                parent=parent,
                side="right"
            )
            counter += 1

            next_level.extend([left, right])

        current_level = next_level

    return root


if __name__ == "__main__":
    with transaction.atomic():
        root = build_mlm_tree(levels=3)
        print("✅ MLM tree created safely")
        print("Root member:", root.auto_id)
        print("Total members:", Member.objects.count())

