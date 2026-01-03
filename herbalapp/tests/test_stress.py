from django.test import TestCase
from herbalapp.models import Member
from decimal import Decimal

class StressTest(TestCase):
    def setUp(self):
        self.members = []
        # Create 50 members with varying BV and binary pairs
        for i in range(1, 51):
            member = Member.objects.create(
                name=f"StressUser{i}",
                package="Gold"
            )
            member.binary_pairs = i  # increasing pairs
            member.binary_income = member.calculate_binary_income()
            member.sponsor_income = Decimal("100") * i
            member.parent_bonus = Decimal("50")
            member.flash_bonus = Decimal("20")
            member.repurchase_wallet = Decimal("10")
            member.bv = 1000 + (i * 50)
            member.rank_reward = member.calculate_rank_reward()
            member.save()
            self.members.append(member)

    def test_stress_payouts(self):
        # Validate all members have non-zero wallet balances
        for member in self.members:
            total_balance = (
                member.binary_income +
                member.sponsor_income +
                member.parent_bonus +
                member.flash_bonus +
                member.repurchase_wallet +
                member.rank_reward
            )
            self.assertGreater(total_balance, 0)
        print(f"Stress Test: {len(self.members)} members validated successfully")

