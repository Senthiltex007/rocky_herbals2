# herbalapp/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from herbalapp.models import Member
from herbalapp.tasks import update_income_task

@receiver(post_save, sender=Member)
def run_income_update_on_new_member(sender, instance, created, **kwargs):
    """
    Trigger automatic income update for new members.
    """
    if created:
        # 🔹 Call celery task for this member
        update_income_task.delay(instance.auto_id)

