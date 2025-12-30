# full_reset_demo.py
# Usage: python manage.py shell < full_reset_demo.py
# ⚠️ WARNING: Backup your DB before running this!

from herbalapp.models import Member
from django.db.models.signals import post_save, post_delete
from herbalapp import signals

post_save.disconnect(signals.auto_trigger_engine, sender=Member)
post_delete.disconnect(signals.auto_trigger_engine, sender=Member)

# 1️⃣ Delete all members safely
print("Deleting all members...")
Member.objects.all().delete()
print("All members deleted.")

# 2️⃣ Prepare new members data
new_members_data = [
    {"name": "Root Member", "phone": "9999999999", "email": "root@example.com"},
    {"name": "Member 1", "phone": "8888888888", "email": "m1@example.com"},
    {"name": "Member 2", "phone": "7777777777", "email": "m2@example.com"},
    {"name": "Member 3", "phone": "6666666666", "email": "m3@example.com"},
    {"name": "Member 4", "phone": "5555555555", "email": "m4@example.com"},
]

# 3️⃣ Add members with auto_id
members_created = []
for idx, data in enumerate(new_members_data, start=1):
    auto_id = f"rocky{idx:03}"  # rocky001, rocky002...
    member = Member.objects.create(
        name=data["name"],
        phone=data["phone"],
        email=data["email"],
        auto_id=auto_id,
        is_active=True
    )
    members_created.append(member)
    print(f"Created member {member.name} with auto_id={member.auto_id}")

# 4️⃣ Assign placement manually (simple demo: binary tree under root)
root_member = members_created[0]

# Assuming Member 1 & 2 placed under root
members_created[1].placement = root_member
members_created[1].position = "left"
members_created[1].save()

members_created[2].placement = root_member
members_created[2].position = "right"
members_created[2].save()

# Members 3 & 4 under Member 1
members_created[3].placement = members_created[1]
members_created[3].position = "left"
members_created[3].save()

members_created[4].placement = members_created[1]
members_created[4].position = "right"
members_created[4].save()

print("Placement setup completed.")

# 5️⃣ Initialize income/commission (demo: all zeros)
for m in members_created:
    m.binary_income = 0
    m.total_left_bv = 0
    m.total_right_bv = 0
    m.commission = 0
    m.save()

print("Income/commission reset to 0 for all members.")
print("✅ Full demo reset & setup completed successfully.")

