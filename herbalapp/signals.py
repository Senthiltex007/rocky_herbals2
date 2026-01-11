# herbalapp/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from herbalapp.models import Member
from herbalapp.management.commands.mlm_run_daily import calculate_member_income_for_day as process_member_daily
from datetime import date

@receiver(post_save, sender=Member)
def auto_run_daily_on_new_member(sender, instance, created, **kwargs):
    if created:
        root = instance
        while root.placement:
            root = root.placement  # find root member

        run_date = date.today()  # default: today
        process_member_daily(root, run_date)

