# herbalapp/ranks.py

# -----------------------------------------
# Rocky Herbals Rank Reward Configuration
# -----------------------------------------

L = 100_000        # 1 Lakh
CR = 10_000_000    # 1 Crore

# Rank reward table (BV matched = min(left_bv, right_bv))
RANKS = [
    # BV, Rank Title, Monthly Salary, Months
    {"min_matched_bv": 25 * CR, "title": "Top Tier",            "monthly": 1 * CR,     "months": 3},
    {"min_matched_bv": 10 * CR, "title": "Triple Diamond",      "monthly": 50 * L,     "months": 4},
    {"min_matched_bv": 5 * CR,  "title": "Double Diamond",      "monthly": 20 * L,     "months": 6},
    {"min_matched_bv": 2.5 * CR,"title": "Diamond Star",        "monthly": 10 * L,     "months": 8},
    {"min_matched_bv": 1 * CR,  "title": "Mono Platinum",       "monthly": 5 * L,      "months": 10},
    {"min_matched_bv": 50 * L,  "title": "Platinum Star",       "monthly": 2 * L,      "months": 12},
    {"min_matched_bv": 25 * L,  "title": "Gilded Gold",         "monthly": 1 * L,      "months": 10},
    {"min_matched_bv": 10 * L,  "title": "Gold Star",           "monthly": 50_000,     "months": 8},
    {"min_matched_bv": 5 * L,   "title": "Shine Silver",        "monthly": 25_000,     "months": 6},
    {"min_matched_bv": 2.5 * L, "title": "Triple Star",         "monthly": 10_000,     "months": 5},
    {"min_matched_bv": 1 * L,   "title": "Double Star",         "monthly": 5_000,      "months": 4},
    {"min_matched_bv": 50_000,  "title": "1st Star",            "monthly": 3_000,      "months": 3},
]

# -----------------------------------------
# Rank Fetch Function
# -----------------------------------------
def get_rank(matched_bv):
    """
    Input:
        matched_bv = min(left_bv, right_bv)

    Output:
        (rank_title, monthly_salary, months)
        or None if no rank achieved
    """

    for r in RANKS:
        if matched_bv >= r["min_matched_bv"]:
            return r["title"], r["monthly"], r["months"]

    return None

