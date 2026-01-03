from herbalapp.models import Member
from datetime import date

run_date = date(2026, 1, 2)

eligible_sponsors = []

for member in Member.objects.all():
    # Rule 3: Must be binary eligible and completed first pair
    if not (member.binary_eligible and member.has_completed_first_pair):
        continue

    placement = member.placement
    sponsor = member.sponsor
    receiver = None

    # Rule 1 & 2
    if placement and sponsor:
        if placement.auto_id == sponsor.auto_id:
            receiver = placement.parent or placement
        else:
            receiver = sponsor

    if not receiver:
        continue

    # Just collect eligible sponsor info
    eligible_sponsors.append((receiver.auto_id, receiver.name, member.auto_id))

# ✅ Print results
for sid, sname, child_id in eligible_sponsors:
    print(f"✅ Sponsor eligible: {sname} ({sid}) from child {child_id}")

