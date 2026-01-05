# herbalapp/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment, Member
from .utils.binary_income import process_member_binary_income
from .utils.sponsor_income import give_sponsor_income


# ==========================================================
# 🔒 HELPER – Dummy Root Check
# ==========================================================
def is_dummy_root(member):
    return member and member.auto_id == "rocky004"


# ==========================================================
# 1️⃣ PAYMENT SUCCESS → INCOME TRIGGER
# ==========================================================
@receiver(post_save, sender=Payment)
def create_income_on_payment(sender, instance, created, **kwargs):
    if not created or instance.status != "Paid":
        return

    member = instance.member

    # 🚫 Skip dummy root
    if is_dummy_root(member):
        return

    print(f"💰 Payment received for Member ID: {member.auto_id}")

    # Binary income
    try:
        process_member_binary_income(member)
        print("🔹 Binary income processed")
    except Exception as e:
        print(f"[signals] Binary income error: {e}")

    # Sponsor income
    try:
        amount = give_sponsor_income(member)
        if amount:
            print(f"🔸 Sponsor income processed: +{amount}")
        else:
            print("🔸 Sponsor income not eligible today")
    except Exception as e:
        print(f"[signals] Sponsor income error: {e}")


# ==========================================================
# 2️⃣ NEW MEMBER ADDED → TREE UPDATE ONLY
# ==========================================================
@receiver(post_save, sender=Member)
def auto_income_on_new_member(sender, instance, created, **kwargs):
    if not created:
        return

    # 🚫 Skip dummy root
    if is_dummy_root(instance):
        return

    print(f"🧩 New Member Added: {instance.auto_id}")

    # Parent binary update (only real parent)
    parent = instance.parent
    if parent and not is_dummy_root(parent):
        try:
            process_member_binary_income(parent)
            print(f"🔹 Parent binary updated: {parent.auto_id}")
        except Exception as e:
            print(f"[signals] Parent binary income error: {e}")

    # Sponsor income (child add based rule)
    try:
        amount = give_sponsor_income(instance)
        if amount:
            print(f"🔸 Sponsor income credited: +{amount}")
        else:
            print("🔸 Sponsor income not credited (rule check)")
    except Exception as e:
        print(f"[signals] Sponsor income error: {e}")

