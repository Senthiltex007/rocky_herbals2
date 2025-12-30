# audit_sponsor.py
import os
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rocky_herbals2.settings")
django.setup()

from herbalapp.models import Member
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day

def audit_child_sponsor(child, L_today=0, R_today=0):
    print(f"\n=== Child audit: {child.auto_id} - {child.name} ===")
    print("Child sponsor:", getattr(child.sponsor, "auto_id", None), "-", getattr(child.sponsor, "name", None))
    print("Child placement:", getattr(child.placement, "auto_id", None), "-", getattr(child.placement, "name", None))

    res = calculate_member_binary_income_for_day(
        left_joins_today=L_today,
        right_joins_today=R_today,
        left_cf_before=child.left_cf,
        right_cf_before=child.right_cf,
        binary_eligible=child.binary_eligible,
    )

    expected_child_cash_for_sponsor = int(res["eligibility_income"] or 0) + int(res["binary_income"] or 0)

    print("Child became eligible today:", res["became_eligible_today"])
    print("Child eligibility income:", res["eligibility_income"])
    print("Child binary pairs:", res["binary_pairs"])
    print("Child binary income (cash):", res["binary_income"])
    print("Child flashout units:", res["flashout_units"])
    print("Child CF after L/R:", res["left_cf_after"], res["right_cf_after"])
    print("Expected child cash to mirror (eligibility + binary):", expected_child_cash_for_sponsor)
    print("Engine child_total_for_sponsor:", res["child_total_for_sponsor"])

if __name__ == "__main__":
    root = Member.objects.get(auto_id="rocky001")
    ganesh = Member.objects.get(name="ganesh")

    audit_child_sponsor(root, L_today=2, R_today=1)
    audit_child_sponsor(ganesh, L_today=2, R_today=1)

