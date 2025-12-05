# mlm_tree_init_formula.py
from herbalapp.models import Member

def create_member(level, number, parent=None, side='left'):
    name = f"Member_L{level}_N{number}"
    auto_id = f"rocky{1000 + level*10 + number}"  # simple auto_id formula
    member = Member.objects.create(name=name, auto_id=auto_id)
    
    # Attach to parent if given
    if parent:
        if side == 'left':
            parent.left_child = member
        else:
            parent.right_child = member
        parent.save()
    
    return member

# ------------------------------
# Example Pyramid Tree
# ------------------------------

# Root
root = create_member(level=0, number=1)

# Level 1
left1 = create_member(level=1, number=1, parent=root, side='left')
right1 = create_member(level=1, number=2, parent=root, side='right')

# Level 2
create_member(level=2, number=1, parent=left1, side='left')
create_member(level=2, number=2, parent=left1, side='right')
create_member(level=2, number=3, parent=right1, side='left')
create_member(level=2, number=4, parent=right1, side='right')

print("Formula-based Pyramid tree created successfully!")

