# mlm_tool.py
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rocky_herbals2.settings")
django.setup()

from herbalapp.models import Member


# -------------------------------------------------
# PRINT TREE (QUERY BASED – SAFE)
# -------------------------------------------------
def print_tree_with_add(member, indent=0):
    if not member:
        return

    print(
        " " * indent
        + f"{member.auto_id} - {member.name} "
        f"(Phone: {member.phone or 'N/A'}, Aadhar: {member.aadhar or 'N/A'})"
    )

    left_children = Member.objects.filter(parent=member, side="left")
    right_children = Member.objects.filter(parent=member, side="right")

    if left_children.exists():
        for c in left_children:
            print_tree_with_add(c, indent + 4)
    else:
        print(" " * (indent + 4) + "+ Add Left Member")

    if right_children.exists():
        for c in right_children:
            print_tree_with_add(c, indent + 4)
    else:
        print(" " * (indent + 4) + "+ Add Right Member")


# -------------------------------------------------
# INTERACTIVE TOOL
# -------------------------------------------------
def interactive_tree(root_member):
    while True:
        print("\n======= CURRENT MLM TREE =======")
        print_tree_with_add(root_member)

        print("\nOptions:")
        print("1. Add Member")
        print("2. Update Member")
        print("3. Delete Member")
        print("4. Exit")

        choice = input("Enter choice (1-4): ").strip()

        # -------------------------
        # ADD MEMBER
        # -------------------------
        if choice == "1":
            parent_id = input("Parent auto_id: ").strip()
            side = input("Side (left/right): ").strip().lower()
            name = input("Name: ").strip()
            phone = input("Phone: ").strip()
            aadhar = input("Aadhar: ").strip()

            if side not in ("left", "right"):
                print("❌ Side must be left or right")
                continue

            try:
                parent = Member.objects.get(auto_id=parent_id)

                exists = Member.objects.filter(parent=parent, side=side).exists()
                if exists:
                    print(f"❌ {side.upper()} side already occupied")
                    continue

                new_member = Member.objects.create(
                    name=name,
                    phone=phone or None,
                    aadhar=aadhar or None,
                    parent=parent,
                    side=side,
                    sponsor=parent,   # default sponsor = parent
                )

                print(f"✅ Member {new_member.auto_id} added successfully")

            except Member.DoesNotExist:
                print("❌ Parent member not found")

        # -------------------------
        # UPDATE MEMBER
        # -------------------------
        elif choice == "2":
            mid = input("Member auto_id to update: ").strip()
            try:
                m = Member.objects.get(auto_id=mid)
                name = input(f"Name ({m.name}): ").strip()
                phone = input(f"Phone ({m.phone or 'N/A'}): ").strip()
                aadhar = input(f"Aadhar ({m.aadhar or 'N/A'}): ").strip()

                if name:
                    m.name = name
                if phone:
                    m.phone = phone
                if aadhar:
                    m.aadhar = aadhar

                m.save()
                print("✅ Member updated successfully")

            except Member.DoesNotExist:
                print("❌ Member not found")

        # -------------------------
        # DELETE MEMBER (SAFE)
        # -------------------------
        elif choice == "3":
            mid = input("Member auto_id to delete: ").strip()
            try:
                m = Member.objects.get(auto_id=mid)

                has_children = Member.objects.filter(parent=m).exists()
                if has_children:
                    print("❌ Cannot delete member with downlines")
                    continue

                m.delete()
                print("✅ Member deleted successfully")

            except Member.DoesNotExist:
                print("❌ Member not found")

        # -------------------------
        # EXIT
        # -------------------------
        elif choice == "4":
            break

        else:
            print("❌ Invalid choice")

