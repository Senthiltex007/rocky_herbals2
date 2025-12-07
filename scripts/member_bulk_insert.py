from herbalapp.models import Member, RockCounter

# STEP 1 — Delete old members + reset RockCounter
Member.objects.all().delete()
RockCounter.objects.filter(name='member').update(last=0)
RockCounter.objects.filter(name='auto_id').update(last=0)

# STEP 2 — Bulk insert 10 new members with Placement + Sponsor
members = []

# First root member (no sponsor/placement)
root = Member.objects.create(name="Member1")
members.append(root)

# Next 9 members under root
for i in range(2, 11):
    m = Member.objects.create(
        name=f"Member{i}",
        sponsor_id=root.id,       # use integer id
        placement_id=root.id      # use integer id
    )
    members.append(m)

# STEP 3 — Print IDs + Placement + Sponsor to confirm
for m in members:
    print(f"DBid={m.id}, MemberID={m.member_id}, Sponsor={m.sponsor_id}, Placement={m.placement_id}")

