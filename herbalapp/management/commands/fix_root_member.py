from django.core.management.base import BaseCommand
from herbalapp.models import Member

ROOT_MEMBER_ID = "rocky002"

class Command(BaseCommand):
    help = "Ensure the root member stays as ROOT and fix tree if needed"

    def handle(self, *args, **kwargs):
        try:
            root_member = Member.objects.get(auto_id=ROOT_MEMBER_ID)
        except Member.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Root member {ROOT_MEMBER_ID} not found!"))
            return

        # 1️⃣ தவறாக parent=None ஆன உறுப்பினர்கள் அனைத்தையும் root_member கீழ் மாற்று
        wrongly_assigned = Member.objects.exclude(auto_id=ROOT_MEMBER_ID).filter(parent=None)
        for member in wrongly_assigned:
            member.parent = root_member
            member.save()
            self.stdout.write(self.style.WARNING(f"Assigned {member.auto_id} under root {ROOT_MEMBER_ID}"))

        # 2️⃣ ரூட் உறுப்பினருக்கு parent=None இடம் கொடு
        root_member.parent = None
        root_member.save()

        self.stdout.write(self.style.SUCCESS(f"✅ Root member {ROOT_MEMBER_ID} fixed successfully!"))

