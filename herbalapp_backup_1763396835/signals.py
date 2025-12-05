from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment, Income, Member
from .utils import generate_income  # your calculation function

@receiver(post_save, sender=Payment)
def create_income_on_payment(sender, instance, created, **kwargs):
    if created and instance.status == 'Paid':
        member = instance.member
        # Example: calculate with dummy values, replace with real logic
        left_pairs = 2
        right_pairs = 2
        bv_left = 50000
        bv_right = 50000

        generate_income(member, left_pairs, right_pairs, bv_left, bv_right)

