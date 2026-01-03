from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Member
from .utils.binary_income import process_member_binary_income

@receiver(post_save, sender=Member)
def member_post_save(sender, instance, created, **kwargs):
    """
    New member add ஆனதும், அல்லது existing member update ஆனதும்
    binary income மற்றும் sponsor income process செய்யும்.
    """
    # created -> new member add ஆனதும்
    # அல்லது பிற updates
    process_member_binary_income(instance)

