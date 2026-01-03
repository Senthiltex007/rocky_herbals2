from django.core.management.base import BaseCommand
from herbalapp.models import Member

class Command(BaseCommand):
    help = "Delete all members and reset binary tree"

    def handle(self, *args, **kwargs):
        Member.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("✅ All members deleted. Tree reset."))

