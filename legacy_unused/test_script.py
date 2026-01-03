from herbalapp.test_engine import test_engine

# --- Case 1: Placement == Sponsor (income goes to parent) ---
print("\n--- Sponsor Income Unlock Day (Placement == Sponsor) ---")
print(test_engine(
    L_today=5,
    R_today=2,
    placement_id="M001",
    sponsor_id="M001",
    sponsor_has_pair=True  # sponsor already has 1:1 pair
))

# --- Case 2: Placement != Sponsor (income goes to sponsor id) ---
print("\n--- Sponsor Income Normal Day (Placement != Sponsor) ---")
print(test_engine(
    L_today=20,
    R_today=20,
    binary_eligible=True,
    placement_id="M002",
    sponsor_id="S001",
    sponsor_has_pair=True  # sponsor already has 1:1 pair
))

# --- Case 3: Sponsor not eligible (no 1:1 pair yet) ---
print("\n--- Sponsor Income Blocked (Sponsor not eligible) ---")
print(test_engine(
    L_today=10,
    R_today=10,
    placement_id="M003",
    sponsor_id="S002",
    sponsor_has_pair=False  # sponsor has no 1:1 pair
))

