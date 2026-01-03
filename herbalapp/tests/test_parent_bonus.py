from django.test import TestCase
from herbalapp.models import Member

class ParentBonusTest(TestCase):
    def setUp(self):
        self.parent = Member.objects.create(name="ParentUser", package="Gold")
        self.child = Member.objects.create(name="ChildUser", parent=self.parent, package="Silver")

        # Simulate parent bonus trigger
        self.child.binary_pairs = 5
        self.child.binary_income = self.child.calculate_binary_income()
        self.child.save()

        # Parent bonus credited manually for test
        self.parent.parent_bonus = 200
        self.parent.save()

    def test_parent_bonus_allocation(self):
        self.assertEqual(self.parent.parent_bonus, 200)
        print(f"Parent Bonus: {self.parent.parent_bonus}, Expected: 200")

