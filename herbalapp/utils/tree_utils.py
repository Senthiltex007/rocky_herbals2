# herbalapp/utils/tree_utils.py
# --------------------------------------------------
# ✅ TREE HELPERS (NO INCOME LOGIC)
# --------------------------------------------------

from herbalapp.models import Member


def get_children(member: Member):
    """Return direct children (placement based)"""
    return Member.objects.filter(placement=member)


def count_leg(member: Member, side: str):
    """
    Count members in LEFT or RIGHT leg (recursive)
    side = "L" or "R"
    """

    def _count(node):
        total = 0
        children = Member.objects.filter(placement=node)
        for c in children:
            total += 1
            total += _count(c)
        return total

    if side == "L" and member.left_child:
        return _count(member.left_child)

    if side == "R" and member.right_child:
        return _count(member.right_child)

    return 0


def get_leg_summary(member: Member):
    """Return left/right counts"""
    return {
        "left": count_leg(member, "L"),
        "right": count_leg(member, "R"),
    }

