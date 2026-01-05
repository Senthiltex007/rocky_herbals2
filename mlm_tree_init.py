# mlm_tree_init.py
# SAFE MLM Tree Init (parent + side based)
# Works with your Binary + Sponsor + Audit logic

from herbalapp.models import Member
from django.db import transaction


def create_member(level, number, parent=None, side=None):
    name = f"Member_L{level}_N{number}"
    auto_id = f"rocky{1000 + level*10 + number}"

    return Member.objects.create(
        name=name,
        auto_id=auto_id,
        parent=parent,
        side=side
    )


if __name__ == "__main__":
    with transaction.atomic():

        # Root
        root = create_member(level=0, number=1)

        # Level 1
        left1 = create_member(level=1, number=1, parent=root, side="left")
        right1 = create_member(level=1, number=2, parent=root, side="right")

        # Level 2
        create_member(level=2, number=1, parent=left1, side="left")
        create_member(level=2, number=2, parent=left1, side="right")

        create_member(level=2, number=3, parent=right1, side="left")
        create_member(level=2, number=4, parent=right1, side="right")

        print("✅ MLM tree created using correct parent + side logic")
        print("Root:", root.auto_id)
        print("Total members:", Member.objects.count())

