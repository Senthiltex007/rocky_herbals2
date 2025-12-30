# fix_tree_links.py
from herbalapp.models import Member

def run():
    for parent in Member.objects.all():
        left_child = Member.objects.filter(placement=parent, side="left").first()
        right_child = Member.objects.filter(placement=parent, side="right").first()

        if left_child and not parent.left_member:
            parent.left_member = left_child
        if right_child and not parent.right_member:
            parent.right_member = right_child

        parent.save()
    print("✅ Tree links updated successfully")

# Run directly when executing the file
if __name__ == "__main__":
    run()

