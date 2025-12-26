from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from herbalapp.models import Member
from herbalapp.mlm_engine_binary import calculate_member_binary_income_for_day

@receiver(post_save, sender=Member)
def trigger_engine_on_new_member(sender, instance, created, **kwargs):
    if not created:
        return

    member = instance
    run_date = timezone.now().date()

    result = calculate_member_binary_income_for_day(
        member.left_joins_today(),
        member.right_joins_today(),
        member.cf_left,
        member.cf_right,
        member.binary_eligible,
        member,
        run_date
    )

    if result["new_binary_eligible"] and not member.binary_eligible:
        member.binary_eligible = True

    member.lifetime_pairs += result["binary_pairs"]
    member.cf_left = result["left_cf_after"]
    member.cf_right = result["right_cf_after"]

    # ✅ Use update() to avoid recursion
    Member.objects.filter(pk=member.pk).update(
        binary_eligible=member.binary_eligible,
        lifetime_pairs=member.lifetime_pairs,
        cf_left=member.cf_left,
        cf_right=member.cf_right
    )

    print(f"⚡ Signal Triggered: Engine run for {member.member_id} on {run_date}")
    print(f"   Binary income={result['binary_income']}, Sponsor mirrored={result['child_total_for_sponsor']}")

