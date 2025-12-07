# herbalapp/signals.py
# ----------------------------------------------------------
# Auto income trigger on:
#   1. Payment Success
#   2. New Member Creation
# ----------------------------------------------------------

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment, Member
from .utils.sponsor_income import give_sponsor_income
from .utils.binary_income import process_member_binary_income
#from .utils.flash_out_bonus import process_out_flash_bonus
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
        try:
            process_member_binary_income(member)
            print("🔹 Binary income processed")
        except Exception as e:
            print(f"[signals] Binary income error: {e}")

        # Sponsor income
        try:
            give_sponsor_income(member)
            print("🔸 Sponsor income processed")
        except Exception as e:
            print(f"[signals] Sponsor income error: {e}")

        # Flash bonus
        try:
            process_flash_bonus(member)
            print("✨ Flash bonus processed")
        except Exception as e:
            print(f"[signals] Flash bonus error: {e}")

        # Salary income
        try:
            bv_left = instance.amount
            bv_right = instance.amount
            add_salary_income(member, bv_left, bv_right)
            print("💼 Salary income added")
        except Exception as e:
            print(f"[signals] Salary income error: {e}")

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
            try:
                process_member_binary_income(instance.parent)
            except Exception as e:
                print(f"[signals] Parent binary income error: {e}")

        # Own income eligibility check
        try:
            process_member_binary_income(instance)
            print("🔹 Auto Binary Trigger Completed")
        except Exception as e:
            print(f"[signals] Member binary income error: {e}")

