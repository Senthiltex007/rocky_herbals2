# create_members.py
from django.utils import timezone
from herbalapp.models import Member

def run():
    # ---- Create Root Sponsor ----
    root_sponsor = Member.objects.create(
        name="Root Sponsor",
        phone="9500435724",
        email="root@rockyherbals.com",
        side="left",
        position="left",
        joined_date=timezone.now().date()   # ✅ correct field name
    )

    # Self‑reference for sponsor, placement, parent
    root_sponsor.sponsor = root_sponsor
    root_sponsor.placement = root_sponsor
    root_sponsor.parent = root_sponsor
    root_sponsor.save()

    print("Root Sponsor created:", root_sponsor.auto_id, root_sponsor.name)

    # ---- Create Root Member under Root Sponsor ----
    root_member = Member.objects.create(
        name="Root Member",
        phone="9500435725",
        email="rootmember@rockyherbals.com",
        side="right",
        position="right",
        parent=root_sponsor,
        sponsor=root_sponsor,
        placement=root_sponsor,
        joined_date=timezone.now().date()
    )

    print("Root Member created:", root_member.auto_id, root_member.name,
          "Parent:", root_member.parent.auto_id,
          "Sponsor:", root_member.sponsor.auto_id,
          "Placement:", root_member.placement.auto_id)

