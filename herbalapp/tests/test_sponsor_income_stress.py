from django.test import TestCase
from herbalapp.models import Member

class SponsorIncomeStressTest(TestCase):
    def setUp(self):
        # Create sponsor
        self.sponsor = Member.objects.create(
            name="Sponsor",
            package="Gold"
        )

        # Create 50 children under sponsor
        self.children = []
        for i in range(50):
            child = Member.objects.create(
                name=f"Child{i+1}",
                sponsor=self.sponsor,
                package="Gold",
                binary_pairs=i+1  # increasing pairs for variety
            )
            child.binary_income = child.calculate_binary_income()
            child.save(update_fields=["binary_income"])
            self.children.append(child)

    def test_sponsor_income_scaling(self):
        """
        Rule: Each child gets 500 per pair.
        Sponsor gets duplication income = sum of all children's binary incomes.
        """
        expected_income = sum(c.calculate_binary_income() for c in self.children)
        sponsor_income = self.sponsor.calculate_sponsor_income()

        self.assertEqual(sponsor_income, expected_income)
        print(f"Sponsor Income (50 children): {sponsor_income}, Expected: {expected_income}")

