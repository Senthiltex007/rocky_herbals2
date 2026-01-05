# herbalapp/mlm_simulation_full_test.py

from datetime import date, timedelta
from herbalapp.models import Member
from herbalapp.mlm_daily_processor import process_daily_income

# -------------------------------
# 1️⃣ CREATE TEST TREE
# -------------------------------
def create_test_tree():
    """
    Creates a multi-level dummy tree for simulation:
    - rocky005 = root (real sponsor)
    - Add left/right children to test 1:1, 1:2, 2:1, flashout, carry forward
    """
    root = Member.objects.get(auto_id="rocky005")

    # Level 1
    guru = Member.objects.create(auto_id="guru", name="Guru", parent=root, placement=root, sponsor=root)
    kavi = Member.objects.create(auto_id="kavi", name="Kavi", parent=root, placement=root, sponsor=root)

    # Level 2
    child1 = Member.objects.create(auto_id="child1", name="Child1", parent=guru, placement=guru, sponsor=guru)
    child2 = Member.objects.create(auto_id="child2", name="Child2", parent=kavi, placement=kavi, sponsor=kavi)
    child3 = Member.objects.create(auto_id="child3", name="Child3", parent=guru, placement=guru, sponsor=guru)
    child4 = Member.objects.create(auto_id="child4", name="Child4", parent=kavi, placement=kavi, sponsor=kavi)
    child5 = Member.objects.create(auto_id="child5", name="Child5", parent=guru, placement=guru, sponsor=guru)

    # Level 3 (to test flashout)
    for i in range(6, 16):
        side_parent = guru if i % 2 == 0 else kavi
        Member.objects.create(
            auto_id=f"child{i}", 
            name=f"Child{i}", 
            parent=side_parent, 
            placement=side_parent, 
            sponsor=side_parent
        )

    return [root, guru, kavi]


# -------------------------------
# 2️⃣ RUN 15-DAY SIMULATION
# -------------------------------
def run_15_day_simulation(start_date=None):
    if start_date is None:
        start_date = date.today()

    members = Member.objects.all().order_by('id')
    print(f"🚀 Starting 15-day simulation from {start_date} for {len(members)} members")

    for day in range(15):
        run_date = start_date + timedelta(days=day)
        print(f"\n📅 Day {day+1} -> {run_date}")

        day_summary = process_daily_income(run_date=run_date)
        for s in day_summary:
            print(
                f"Member: {s['member']}, "
                f"Binary: {s['binary_income']}, "
                f"Flashout: {s['flashout_income']}, "
                f"Sponsor: {s['sponsor_income']}, "
                f"Total: {s['total_income']}"
            )


# -------------------------------
# 3️⃣ MAIN EXECUTION
# -------------------------------
if __name__ == "__main__":
    create_test_tree()
    run_15_day_simulation()

