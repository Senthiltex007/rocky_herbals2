from django.core.management.base import BaseCommand
from herbalapp.models import Member

class Command(BaseCommand):
    help = 'Update left_child and right_child fields for existing members'

    def handle(self, *args, **options):
        members = Member.objects.all()
        count = 0
        for member in members:
            # Find left and right children
            left = Member.objects.filter(parent=member, side='left').first()
            right = Member.objects.filter(parent=member, side='right').first()

            if left:
                member.left_child = left
            if right:
                member.right_child = right

            member.save()
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Updated left/right child for {count} members'))

