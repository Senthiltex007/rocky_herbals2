from django.utils import timezone


def calculate_member_binary_income_for_day(
    left_joins_today: int,
    right_joins_today: int,
    left_cf_before: int,
    right_cf_before: int,
    binary_eligible: bool,
):
    """
    Rocky Herbals – Binary Engine (1:2 / 2:1 eligibility + unlimited 1:1 after eligibility)

    Rules (தமிழில் சுருக்கம்):
    - Lifetime eligibility: ONLY 1:2 அல்லது 2:1; 1:1-க்கு eligibility கிடையாது.
    - Eligibility bonus: ₹500 (ஒரு முறை மட்டும்).
    - Eligibility வந்த பிறகு: unlimited 1:1 pairs, எந்த daily limit இல்லை.
    - Flashout, washout எதுவும் இல்லை.
    - Carry forward: leftover single side counts (L அல்லது R) மட்டும் அவர்கள் CF-ஆக சேமிக்கப்படும்.
    - Sponsor income: இந்த function sponsor income கணக்கே பண்ணாது;
      ஆனா sponsor கணக்குக்கு தேவையான child total-ஐ return பண்ணும்.
    """

    PAIR_VALUE = 500          # ஒவ்வொரு 1:1 pair க்கும் ₹500
    ELIGIBILITY_BONUS = 500   # 1:2 அல்லது 2:1 மூலம் வரும் eligibility bonus

    # ---------------------------------
    # 1. இன்று available ஆன மொத்த left/right
    # ---------------------------------
    L = left_joins_today + left_cf_before
    R = right_joins_today + right_cf_before

    new_binary_eligible = binary_eligible
    eligibility_income = 0
    became_eligible_today = False  # sponsor & report க்கு பயன்படும் flag

    # ---------------------------------
    # 2. Lifetime eligibility check
    # ---------------------------------
    if not binary_eligible:
        # 1:2 or 2:1 pattern மட்டும் பார்க்கணும்
        if (L >= 1 and R >= 2) or (L >= 2 and R >= 1):
            new_binary_eligible = True
            became_eligible_today = True
            eligibility_income = ELIGIBILITY_BONUS

            # Eligibility க்கு பயன்படுத்தும் pattern-ஐ deduct பண்ணணும்
            # இரண்டு pattern-மும் possible ஆ இருந்தா, balance better ஆகும் மாதிரி choose பண்ணணும்.
            if L >= 2 and R >= 2:
                if L > R:
                    # Left heavy -> 2:1 use
                    L -= 2
                    R -= 1
                else:
                    # Right heavy அல்லது equal -> 1:2 use
                    L -= 1
                    R -= 2
            else:
                # ஒரு pattern மட்டும்தான் possible
                if L >= 1 and R >= 2:
                    # 1:2 eligibility
                    L -= 1
                    R -= 2
                else:
                    # 2:1 eligibility
                    L -= 2
                    R -= 1
        else:
            # இன்னும் eligible இல்ல; ஜோடி அமைக்க அனுமதி இல்லை.
            # எந்த pairs-மும் binary income க்கு use ஆகாது; ஆனால் washout இல்லை,
            # full L/R carry forward ஆகும்.
            left_cf_after = L
            right_cf_after = R
            return {
                "new_binary_eligible": new_binary_eligible,   # இன்னும் False
                "became_eligible_today": False,               # இன்று eligibility வந்ததில்லை
                "eligibility_income": 0,
                "binary_pairs": 0,
                "binary_income": 0,
                "left_cf_after": left_cf_after,
                "right_cf_after": right_cf_after,
                "total_income": 0,
                # கீழே இதிலிருந்து sponsor calculation செய்யலாம்:
                "child_total_for_sponsor": 0,
            }

    # ---------------------------------
    # 3. Eligibility வந்த பிறகு: unlimited 1:1 binary
    # ---------------------------------
    # இங்க வரும்போது member already eligible அல்லது இப்போதான் eligible ஆகியிருக்கிறார்.
    total_pairs = min(L, R)           # எல்லா 1:1 pairs-மும் allowed
    binary_income = total_pairs * PAIR_VALUE

    # பயன்படுத்திய pairs-ஐ deduct பண்ணு
    L -= total_pairs
    R -= total_pairs

    # ---------------------------------
    # 4. Carry forward
    # ---------------------------------
    left_cf_after = L
    right_cf_after = R

    # ---------------------------------
    # 5. Total income (child க்கு)
    # ---------------------------------
    total_income = eligibility_income + binary_income

    # Sponsor engine க்கு முக்கியமான data:
    #   child_total_for_sponsor = eligibility_income + binary_income
    # Sponsor logic (parent flag check + income credit) outer layer-ல செய்யணும்.
    child_total_for_sponsor = total_income

    return {
        "new_binary_eligible": new_binary_eligible,     # bool
        "became_eligible_today": became_eligible_today, # இன்று eligibility வந்ததா?
        "eligibility_income": eligibility_income,       # ₹
        "binary_pairs": total_pairs,                    # இன்று 1:1 pairs count
        "binary_income": binary_income,                 # ₹
        "left_cf_after": left_cf_after,                 # CF L
        "right_cf_after": right_cf_after,               # CF R
        "total_income": total_income,                   # இன்று child க்கு மொத்த income
        "child_total_for_sponsor": child_total_for_sponsor,  # sponsor க்கு base amount
    }


# -----------------------------
# CORRECT ROCKY HERBALS RANK LOGIC
# -----------------------------
def determine_rank_from_bv(bv: int):
    """
    Returns:
        (rank_title, monthly_salary, months)
        or None if no rank achieved
    """

    # 25 Cr
    if bv >= 250000000:
        return ("Top Tier", 10000000, 3)

    # 10 Cr
    if bv >= 100000000:
        return ("Triple Diamond", 5000000, 4)

    # 5 Cr
    if bv >= 50000000:
        return ("Double Diamond", 2000000, 6)

    # 2.5 Cr
    if bv >= 25000000:
        return ("Diamond Star", 1000000, 8)

    # 1 Cr
    if bv >= 10000000:
        return ("Mono Platinum", 500000, 10)

    # 50 Lakh
    if bv >= 5000000:
        return ("Platinum Star", 200000, 12)

    # 25 Lakh
    if bv >= 2500000:
        return ("Gilded Gold", 100000, 10)

    # 10 Lakh
    if bv >= 1000000:
        return ("Gold Star", 50000, 8)

    # 5 Lakh
    if bv >= 500000:
        return ("Shine Silver", 25000, 6)

    # 2.5 Lakh
    if bv >= 250000:
        return ("Triple Star", 10000, 5)

    # 1 Lakh
    if bv >= 100000:
        return ("Double Star", 5000, 4)

    # 50,000
    if bv >= 50000:
        return ("1st Star", 3000, 3)

    return None

