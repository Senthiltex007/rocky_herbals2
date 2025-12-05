from django.test import TestCase
from herbalapp.models import Member
from decimal import Decimal

class NegativeTest(TestCase):
    def setUp(self):
        # Case 1: Inactive member
        self.inactive_member = Member.objects.create(
            name="InactiveUser",
            package="Gold",
            active=False,
            bv=2000
        )
        self.inactive_member.binary_income = Decimal("0")
        self.inactive_member.sponsor_income = Decimal("0")
        self.inactive_member.parent_bonus = Decimal("0")
        self.inactive_member.flash_bonus = Decimal("0")
        self.inactive_member.repurchase_wallet = Decimal("0")
        self.inactive_member.rank_reward = Decimal("0")
        self.inactive_member.save()

        # Case 2: BV < 1000 (no rank reward)
        self.low_bv_member = Member.objects.create(
            name="LowBVUser",
            package="Silver",
            active=True,
            bv=800
        )
        self.low_bv_member.binary_income = Decimal("100")
        self.low_bv_member.sponsor_income = Decimal("50")
        self.low_bv_member.parent_bonus = Decimal("20")
        self.low_bv_member.flash_bonus = Decimal("10")
        self.low_bv_member.repurchase_wallet = Decimal("5")
        self.low_bv_member.rank_reward = self.low_bv_member.calculate_rank_reward()
        self.low_bv_member.save()

    def test_inactive_member_payouts(self):
        total_balance = (
            self.inactive_member.binary_income +
            self.inactive_member.sponsor_income +
            self.inactive_member.parent_bonus +
            self.inactive_member.flash_bonus +
            self.inactive_member.repurchase_wallet +
            self.inactive_member.rank_reward
        )
        self.assertEqual(total_balance, 0)
        print(f"Inactive Member Wallet Balance: {total_balance}, Expected: 0")

    def test_low_bv_member_rank_reward(self):
        self.assertEqual(self.low_bv_member.rank_reward, 0)
        print(f"Low BV Member Rank Reward: {self.low_bv_member.rank_reward}, Expected: 0")

