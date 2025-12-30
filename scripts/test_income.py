from herbalapp.models import Member

def calculate_income(member):
    # Skip root sponsor (dummy node)
    if member.auto_id == "rootsponsor001":
        return  # no income calculation

    # Normal income calculation logic here
    print(f"Calculating income for {member.auto_id}")


def run():
    root = Member.objects.get(auto_id="rocky001")
    rootsponsor = Member.objects.get(auto_id="rootsponsor001")

    calculate_income(root)         # Root member → calculation runs
    calculate_income(rootsponsor)  # Root sponsor → skipped

