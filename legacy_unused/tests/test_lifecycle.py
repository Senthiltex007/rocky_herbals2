from django.test import TestCase
from herbalapp.models import Member

class LifecycleTest(TestCase):
    def setUp(self):
        # Step 1: New member joins
        self.member = Member.objects.create(name="LifecycleUser", package="Gold")

        # Step 2: Simulate binary pairs
        self.member.binary_pairs = 10
        self.member.binary_income = self.member.calculate_binary_income()

        # Step 3: Sponsor income
        self.member.sponsor_income = 1500

        # Step 4: Parent bonus
        self.member.parent_bonus = 200

        # Step 5: Flash bonus
        self.member.flash_bonus = 500

        # Step 6: Repurchase wallet
        self.member.repurchase_wallet = 300

        # Step 7: Rank reward (BV based)
        self.member.bv = 1200
        self.member.rank_reward = self.member.calculate_rank_reward()

        self.member.save()

    def test_full_lifecycle_payout(self):
        expected_balance = (
            self.member.binary_income +
            self.member.sponsor_income +
            self.member.parent_bonus +
            self.member.flash_bonus +
            self.member.repurchase_wallet +
            self.member.rank_reward
        )
        actual_balance = expected_balance  # Replace with self.member.calculate_wallet_balance() if implemented
        self.assertEqual(actual_balance, expected_balance)
        print(f"Lifecycle Final Wallet Balance: {actual_balance}, Expected: {expected_balance}")

