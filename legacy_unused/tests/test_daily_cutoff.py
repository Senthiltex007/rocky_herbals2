from django.test import TestCase
from django.utils import timezone
from herbalapp.models import Member

class DailyCutOffTest(TestCase):
    def setUp(self):
        self.sponsor = Member.objects.create(
            name="Sponsor",
            package="Gold"
        )

        # Create children joined today
        for i in range(10):
            Member.objects.create(
                name=f"ChildToday{i+1}",
                sponsor=self.sponsor,
                package="Gold",
                binary_pairs=2,
                joined_date=timezone.now().date()
            )

        # Create children joined yesterday
        yesterday = timezone.now().date() - timezone.timedelta(days=1)
        for i in range(5):
            Member.objects.create(
                name=f"ChildYesterday{i+1}",
                sponsor=self.sponsor,
                package="Gold",
                binary_pairs=3,
                joined_date=yesterday
            )

    def test_daily_cutoff_income(self):
        income_data = self.sponsor.calculate_full_income()

        new_members_today = self.sponsor.get_new_members_today_count()
        self.assertEqual(new_members_today, 10)

        print(f"New Members Today: {new_members_today}")
        print(f"Binary Income Today: {income_data['binary_income']}")
        print(f"Flash Bonus Today: {income_data['flash_bonus']}")
        print(f"Sponsor Income Today: {income_data['sponsor_income']}")

