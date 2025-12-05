from django.test import TestCase
from django.utils import timezone
from herbalapp.models import Member

class FlashBonusWashoutTest(TestCase):
    def setUp(self):
        # Create sponsor
        self.sponsor = Member.objects.create(
            name="Sponsor",
            package="Gold"
        )

        # Create 30 children joined today (15 pairs)
        for i in range(30):
            Member.objects.create(
                name=f"Child{i+1}",
                sponsor=self.sponsor,
                package="Gold",
                joined_date=timezone.now().date()
            )

    def test_flash_bonus_and_washout(self):
        """
        Rule:
        - Daily binary cut-off = 5 pairs → 2500
        - Flash bonus = next 9 units (45 pairs) → 1000 per unit
        - Washout = remaining members not paired
        """
        income_data = self.sponsor.calculate_full_income()

        new_members_today = self.sponsor.get_new_members_today_count()
        self.assertEqual(new_members_today, 30)

        print(f"New Members Today: {new_members_today}")
        print(f"Binary Income Today: {income_data['binary_income']}")
        print(f"Flash Bonus Today: {income_data['flash_bonus']}")
        print(f"Wash Out Members: {income_data['wash_out_members']}")
        print(f"Total Income All: {income_data['total_income_all']}")

