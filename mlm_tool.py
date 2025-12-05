# mlm_tool.py
from herbalapp.models import Member

def print_tree_with_add(member, indent=0):
    if member:
        print(" " * indent + f"{member.auto_id} - {member.name} (Phone: {member.phone or 'N/A'}, Aadhar: {member.aadhar or 'N/A'})")
        print_tree_with_add(member.left_child, indent + 4)
        print_tree_with_add(member.right_child, indent + 4)
    else:
        print(" " * indent + "+ Add Member")

def interactive_tree(member):
    while True:
        print("\n--- Current Pyramid Tree ---")
        print_tree_with_add(member)

        print("\nOptions:")
        print("1. Add Member")
        print("2. Replace Member")
        print("3. Delete Member")
        print("4. Exit")

        choice = input("Enter your choice (1-4): ")

        if choice == "1":
            parent_id = input("Enter parent auto_id to add under: ")
            side = input("Enter side (left/right, default: left): ") or "left"
            name = input("Enter new member name: ")
            phone = input("Enter phone number: ")
            aadhar = input("Enter Aadhar number: ")

            try:
                parent_member = Member.objects.get(auto_id=parent_id)
                new_member = Member(name=name, phone=phone, aadhar=aadhar)
                new_member.save()

                if side.lower() == "left":
                    parent_member.left_child = new_member
                else:
                    parent_member.right_child = new_member
                parent_member.save()

                print(f"Member {name} added successfully!")

            except Member.DoesNotExist:
                print("Parent member not found!")

        elif choice == "2":
            replace_id = input("Enter auto_id of member to replace: ")
            try:
                m = Member.objects.get(auto_id=replace_id)
                new_name = input(f"Enter new name (current: {m.name}): ")
                new_phone = input(f"Enter new phone (current: {m.phone or 'N/A'}): ")
                new_aadhar = input(f"Enter new Aadhar (current: {m.aadhar or 'N/A'}): ")

                m.name = new_name or m.name
                m.phone = new_phone or m.phone
                m.aadhar = new_aadhar or m.aadhar
                m.save()

                print(f"Member {replace_id} updated successfully!")
            except Member.DoesNotExist:
                print("Member not found!")

        elif choice == "3":
            del_id = input("Enter auto_id of member to delete: ")
            try:
                m = Member.objects.get(auto_id=del_id)
                parent = m.parent
                if parent:
                    if parent.left_child == m:
                        parent.left_child = None
                    elif parent.right_child == m:
                        parent.right_child = None
                    parent.save()
                m.delete()
                print(f"Member {del_id} deleted successfully!")
            except Member.DoesNotExist:
                print("Member not found!")

        elif choice == "4":
            break
        else:
            print("Invalid choice! Try again.")

