from django.core.management.base import BaseCommand
from herbalapp.mlm.sponsor_engine import run_sponsor_engine
from herbalapp.models import Member
from django.utils import timezone

class Command(BaseCommand):
    help = "Run Sponsor Income Engine for all members"

    def handle(self, *args, **options):
        today = timezone.localdate()
        self.stdout.write(self.style.NOTICE(f"🚀 Running Sponsor Income Engine for {today}"))

        for member in Member.objects.exclude(auto_id="rocky001"):
            run_sponsor_engine(member, today=today)

        self.stdout.write(self.style.SUCCESS("🎯 Sponsor Income Engine Completed"))

