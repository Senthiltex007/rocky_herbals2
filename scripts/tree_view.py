import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rocky_sri_herbals.settings")
django.setup()

from herbalapp.models import Member

def audit_and_fix():
    print("ID | AutoID | Name | Eligible | Left | Right | LeftCF | RightCF | LifetimePairs | TotalIncome")
    print("-"*95)
    for m in Member.objects.all().order_by("id"):
        left_count = Member.objects.filter(placement=m, side="left").count()
        right_count = Member.objects.filter(placement=m, side="right").count()

        # ✅ Flip eligibility if both sides filled
        if left_count > 0 and right_count > 0 and not m.binary_eligible:
            m.binary_eligible = True
            m.save(update_fields=["binary_eligible"])

        print(f"{m.id} | {m.auto_id} | {m.name} | {m.binary_eligible} | "
              f"{left_count} | {right_count} | {m.left_cf} | {m.right_cf} | "
              f"{m.lifetime_pairs} | {getattr(m,'total_income',0)}")

# Run the audit
audit_and_fix()

