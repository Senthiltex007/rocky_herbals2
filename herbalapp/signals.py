# herbalapp/signals.py
# 🚫 SIGNAL TEMPORARILY DISABLED FOR MLM ENGINE TESTING

# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from herbalapp.models import Member
# from herbalapp.tasks import run_engine_task

# @receiver(post_save, sender=Member)
# def run_engine_after_member_save(sender, instance, created, **kwargs):
#     """
#     Trigger MLM engine automatically after a new member is saved.
#     Only runs once per new member.
#     """
#     if not created:
#         return
#
#     run_engine_task.delay()

