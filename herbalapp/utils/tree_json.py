# herbalapp/utils/tree_json.py
# ----------------------------------------------------------
# ✅ Build recursive JSON for Treant.js genealogy diagram
# ----------------------------------------------------------

from herbalapp.models import Member

def build_tree_json(member: Member):
    """
    Recursively build JSON structure for Treant.js
    Each node clickable → opens /tree/dynamic/<auto_id>/
    Includes avatar + rank/package info
    """
    node = {
        "text": {
            "name": f"{member.auto_id} - {member.name}",
            # ✅ Safe fallback: if rank_title not in model, show N/A
            "title": f"Rank: {getattr(member, 'rank_title', 'N/A')}"
        },
        "HTMLclass": "clickable-node",
        "link": { "href": f"/tree/dynamic/{member.auto_id}/" },
        "image": f"/media/avatars/{member.auto_id}.png"   # optional avatar path
    }

    # ✅ children based on placement field
    children = Member.objects.filter(placement=member).order_by("position")
    if children.exists():
        node["children"] = [build_tree_json(child) for child in children]

    return node

