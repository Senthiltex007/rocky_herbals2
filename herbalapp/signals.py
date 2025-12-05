# herbalapp/signals.py
# ----------------------------------------------------------
# Auto income trigger on:
#   1. Payment Success (existing)
#   2. New Member Creation (NEW added)
# ----------------------------------------------------------

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment, Member
from .utils.binary_income import process_member_binary_income
from .services import add_salary_income


# ==========================================================
# 1️⃣ PAYMENT SUCCESS → INCOME TRIGGER
# ==========================================================
@receiver(post_save, sender=Payment)
def create_income_on_payment(sender, instance, created, **kwargs):
    if created and instance.status == 'Paid':
        member = instance.member
        print(f"💰 Payment received for Member ID: {member.member_id}")

        # Binary income
        process_member_binary_income(member)
        print("🔹 Binary income processed")

        # Temporary salary income
        bv_left = instance.amount
        bv_right = instance.amount
        add_salary_income(member, bv_left, bv_right)
        print("🔸 Salary income added")

    else:
        print("ℹ Payment updated or not Paid → Income skipped")



# ==========================================================
# 2️⃣ NEW MEMBER ADDED → AUTO BINARY COUNT UPDATE
# ==========================================================
@receiver(post_save, sender=Member)
def auto_binary_on_new_member(sender, instance, created, **kwargs):
    if created:
        # Parent income calculate (child attach போதும்)
        if instance.parent:
            print(f"🧩 New Member Added: {instance.member_id} → Parent: {instance.parent.member_id}")
            process_member_binary_income(instance.parent)

        # Own income eligibility check
        process_member_binary_income(instance)
        print("🔹 Auto Binary Trigger Completed")

