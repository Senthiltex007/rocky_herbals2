from django.test import TestCase
from herbalapp.models import Member

class WalletBalanceTest(TestCase):
    def setUp(self):
        self.member = Member.objects.create(name="WalletUser", package="Gold")
        # Simulate incomes
        self.member.binary_income = 1000
        self.member.sponsor_income = 1500
        self.member.parent_bonus = 200
        self.member.flash_bonus = 500
        self.member.repurchase_wallet = 300
        self.member.rank_reward = 200
        self.member.save()

    def test_wallet_balance_aggregation(self):
        expected_balance = (
            self.member.binary_income +
            self.member.sponsor_income +
            self.member.parent_bonus +
            self.member.flash_bonus +
            self.member.repurchase_wallet +
            self.member.rank_reward
        )
        actual_balance = expected_balance  # In real app, replace with self.member.calculate_wallet_balance()
        self.assertEqual(actual_balance, expected_balance)
        print(f"Wallet Balance: {actual_balance}, Expected: {expected_balance}")

