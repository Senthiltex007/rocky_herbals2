from django.test import TestCase
from herbalapp.models import Member

class BinaryIncomeTest(TestCase):
    def setUp(self):
        self.member = Member.objects.create(name="BinaryUser", package="Gold")
        self.member.binary_pairs = 10
        self.member.binary_income = self.member.calculate_binary_income()
        self.member.save()

    def test_binary_income_calculation(self):
        expected_income = self.member.calculate_binary_income()
        self.assertEqual(self.member.binary_income, expected_income)
        print(f"Binary Income: {self.member.binary_income}, Expected: {expected_income}")

