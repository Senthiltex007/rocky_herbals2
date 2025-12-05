# mlm_tree_dynamic.py
#
# Formula-based pyramid tree generator for Rocky Herbals project.
# Usage (from project root):
#   nano mlm_tree_dynamic.py   -> paste this file and save
#   python manage.py shell -c "exec(open('mlm_tree_dynamic.py').read())"
#
from herbalapp.models import Member
from django.db import transaction

def create_member(name, phone=None, aadhar_number=None):
    """
    Create a Member record. Returns the created Member instance.
    """
    # If you want to avoid duplicates in repeated runs, you can uncomment
    # the lookup below (search by name) and return existing entry instead.
    # existing = Member.objects.filter(name=name).first()
    # if existing:
    #     return existing

    return Member.objects.create(
        name=name,
        phone=phone,
        aadhar_number=aadhar_number
    )

def attach_child(parent, child, side='left'):
    """
    Attach 'child' as left_child or right_child of 'parent' and save parent.
    """
    if not parent or not child:
        return
    if side.lower() == 'left':
        parent.left_child = child
    else:
        parent.right_child = child
    parent.save()

def build_formula_tree(levels=3, root_name_prefix="Member"):
    """
    Build a full binary tree with given number of levels.
    levels=1  -> only root
    levels=2  -> root + its 2 children
    levels=3  -> root + 2 + 4 = total 7 nodes
    ...
    This function uses a deterministic naming & simple phone/aadhar formulas.
    """
    if levels < 1:
        raise ValueError("levels must be >= 1")

    # optional: clear existing test members (UNCOMMENT if you want)
    # Member.objects.all().delete()

    counter = 1
    phone_base = 9500000000
    aadhar_base = 111100000000

    # Create root
    root_name = f"{root_name_prefix}_L0_N1"
    root_phone = str(phone_base + counter)
    root_aadhar = str(aadhar_base + counter)
    root = create_member(root_name, phone=root_phone, aadhar_number=root_aadhar)
    counter += 1

    # BFS by levels
    current_level = [root]

    for lvl in range(1, levels):
        next_level = []
        for idx, parent in enumerate(current_level, start=1):
            # left child
            left_name = f"{root_name_prefix}_L{lvl}_N{idx*2-1}"
            left_phone = str(phone_base + counter)
            left_aadhar = str(aadhar_base + counter)
            left_child = create_member(left_name, phone=left_phone, aadhar_number=left_aadhar)
            attach_child(parent, left_child, side='left')
            next_level.append(left_child)
            counter += 1

            # right child
            right_name = f"{root_name_prefix}_L{lvl}_N{idx*2}"
            right_phone = str(phone_base + counter)
            right_aadhar = str(aadhar_base + counter)
            right_child = create_member(right_name, phone=right_phone, aadhar_number=right_aadhar)
            attach_child(parent, right_child, side='right')
            next_level.append(right_child)
            counter += 1

        current_level = next_level

    return root

if __name__ == "__main__":
    # Run inside a django shell context (manage.py shell -c "exec(...)")
    # Wrap in transaction.atomic to avoid partial writes on error
    with transaction.atomic():
        # Change 'levels' to desired depth (e.g., 4 for 15 nodes)
        root_member = build_formula_tree(levels=3, root_name_prefix="Member")
        print("Formula-based pyramid tree created. Root:", root_member.auto_id, root_member.name)
        # Print summary
        total = Member.objects.count()
        print(f"Total members in DB now: {total}")

