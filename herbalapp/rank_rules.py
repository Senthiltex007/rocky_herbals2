# herbalapp/rank_rules.py

RANK_SLABS = [
    # required_matched_bv, rank_title, monthly_income, months
    (50_000,     "First Star",     3_000,     3),
    (100_000,    "Double Star",    5_000,     4),
    (250_000,    "Triple Star",   10_000,     5),
    (500_000,    "Silver Star",   25_000,     6),
    (1_000_000,  "Shining Silver",50_000,     8),
    (2_500_000,  "Gold Star",    100_000,    10),
    (5_000_000,  "Gilded Gold",  200_000,    12),
    (10_000_000, "Platinum Star",500_000,    10),
    (25_000_000, "Mono Platinum",1_000_000,   8),
    (50_000_000, "Diamond Star", 2_000_000,   6),
    (100_000_000,"Double Diamond",5_000_000,  4),
    (250_000_000,"Triple Diamond",10_000_000, 3),
]

