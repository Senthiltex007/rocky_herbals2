from django.test import TestCase
from herbalapp.models import Member
from decimal import Decimal

class ActualIncomeTest(TestCase):
    def setUp(self):
        # Create a Gold member
        self.member = Member.objects.create(name="ActualUser", package="Gold")

        # Assign actual programme values
        self.member.binary_pairs = 25   # Example: 25 pairs
        self.member.binary_income = Decimal("2500")  # Actual binary income
        self.member.sponsor_income = Decimal("1500")
        self.member.parent_bonus = Decimal("200")
        self.member.flash_bonus = Decimal("500")
        self.member.repurchase_wallet = Decimal("300")
        self.member.bv = 1200
        self.member.rank_reward = self.member.calculate_rank_reward()
        self.member.save()

    def test_actual_income_values(self):
        # Expected values as per programme set
        expected_binary_income = Decimal("2500")
        expected_sponsor_income = Decimal("1500")
        expected_parent_bonus = Decimal("200")
        expected_flash_bonus = Decimal("500")
        expected_repurchase_wallet = Decimal("300")
        expected_rank_reward = Decimal("200")

        # Assertions
        self.assertEqual(self.member.binary_income, expected_binary_income)
        self.assertEqual(self.member.sponsor_income, expected_sponsor_income)
        self.assertEqual(self.member.parent_bonus, expected_parent_bonus)
        self.assertEqual(self.member.flash_bonus, expected_flash_bonus)
        self.assertEqual(self.member.repurchase_wallet, expected_repurchase_wallet)
        self.assertEqual(self.member.rank_reward, expected_rank_reward)

        # Final wallet balance check
        expected_balance = (
            expected_binary_income +
            expected_sponsor_income +
            expected_parent_bonus +
            expected_flash_bonus +
            expected_repurchase_wallet +
            expected_rank_reward
        )
        actual_balance = (
            self.member.binary_income +
            self.member.sponsor_income +
            self.member.parent_bonus +
            self.member.flash_bonus +
            self.member.repurchase_wallet +
            self.member.rank_reward
        )
        self.assertEqual(actual_balance, expected_balance)
        print(f"Actual Programme Wallet Balance: {actual_balance}, Expected: {expected_balance}")

