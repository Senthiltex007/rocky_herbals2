import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rocky_herbals2.settings")

django.setup()

from herbalapp.models import Member

print("🔁 Resetting today counts...")
Member.objects.update(left_new_today=0, right_new_today=0)

members = Member.objects.exclude(auto_id="rocky004")

for m in members:
    p = m.parent
    s = m.side

    while p and p.auto_id != "rocky004":
        if s == "L":
            p.left_new_today += 1
        elif s == "R":
            p.right_new_today += 1

        p.save(update_fields=["left_new_today", "right_new_today"])
        p = p.parent

print("✅ Today join counts rebuilt")

root = Member.objects.get(auto_id="rocky005")
print("📊 rocky005 -> LEFT:", root.left_new_today, "RIGHT:", root.right_new_today)

