from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from datetime import timedelta
from herbalapp.models import Member

# Use your existing engine function (best counts)
from herbalapp.mlm.final_master_engine import count_all_descendants

def tree_modern_page(request, root_id="rocky002"):
    return render(request, "tree.html", {"root_id": root_id})

def tree_data(request, root_id):
    root = get_object_or_404(Member, auto_id=root_id)

    collected = []

    def dfs(parent):
        children = Member.objects.filter(parent=parent, is_active=True).order_by("id")
        for c in children:
            collected.append(c)
            dfs(c)

    dfs(root)

    def avatar_url(m):
        img = getattr(m, "avatar", None)
        if img and hasattr(img, "url"):
            return img.url
        return "/static/img/default-avatar.png"

    nodes = [{
        "data": {
            "id": root.auto_id,
            "name": root.name,
            "bv": str(root.bv or 0),
            "avatar": avatar_url(root),
        }
    }]

    edges = []

    for m in collected:
        nodes.append({
            "data": {
                "id": m.auto_id,
                "name": m.name,
                "bv": str(m.bv or 0),
                "avatar": avatar_url(m),
            }
        })
        if m.parent:
            edges.append({
                "data": {
                    "source": m.parent.auto_id,
                    "target": m.auto_id
                }
            })

    return JsonResponse({"nodes": nodes, "edges": edges})

def member_details_api(request, member_id):
    m = get_object_or_404(Member, auto_id=member_id)

    left_count = count_all_descendants(m, "left", as_of_date=None)
    right_count = count_all_descendants(m, "right", as_of_date=None)

    img = getattr(m, "avatar", None)
    avatar = img.url if img and hasattr(img, "url") else "/static/img/default-avatar.png"

    return JsonResponse({
        "auto_id": m.auto_id,
        "name": m.name,
        "joined_date": str(m.joined_date) if m.joined_date else "",
        "left_count": left_count,
        "right_count": right_count,
        "bv": str(m.bv or 0),
        "avatar": avatar,
        "sponsor": m.sponsor.auto_id if m.sponsor else "",
        "parent": m.parent.auto_id if m.parent else "",
        "side": m.side or "",
    })

