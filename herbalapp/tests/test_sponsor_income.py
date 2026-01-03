from django.test import TestCase
from herbalapp.models import Member

class SponsorIncomeTest(TestCase):
    def setUp(self):
        # Create sponsor (auto_id will be generated automatically)
        self.sponsor = Member.objects.create(
            name="Sponsor",
            package="Gold"
        )

        # Create children with sponsor reference
        self.child1 = Member.objects.create(
            name="Child1",
            sponsor=self.sponsor,
            package="Gold",
            binary_pairs=5
        )
        self.child2 = Member.objects.create(
            name="Child2",
            sponsor=self.sponsor,
            package="Silver",
            binary_pairs=10
        )

        # Calculate binary incomes for children
        self.child1.binary_income = self.child1.calculate_binary_income()
        self.child1.save(update_fields=["binary_income"])

        self.child2.binary_income = self.child2.calculate_binary_income()
        self.child2.save(update_fields=["binary_income"])

    def test_sponsor_income_calculation(self):
        """
        Rule: Each child gets 500 per pair.
        Sponsor gets the same duplication income (sum of children’s binary incomes).
        """
        expected_income = (
            self.child1.calculate_binary_income() +
            self.child2.calculate_binary_income()
        )

        sponsor_income = self.sponsor.calculate_sponsor_income()

        self.assertEqual(sponsor_income, expected_income)
        print(f"Sponsor Income: {sponsor_income}, Expected: {expected_income}")

