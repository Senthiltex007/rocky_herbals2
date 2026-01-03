from django.test import TestCase
from herbalapp.models import Member
from decimal import Decimal
import time

class PerformanceTest(TestCase):
    def setUp(self):
        self.members = []
        start_time = time.time()

        # Create 500 members with varying BV and incomes
        for i in range(1, 501):
            member = Member.objects.create(
                name=f"PerfUser{i}",
                package="Gold",
                bv=1000 + (i * 10)
            )
            member.binary_pairs = i
            member.binary_income = member.calculate_binary_income()
            member.sponsor_income = Decimal("100") * i
            member.parent_bonus = Decimal("50")
            member.flash_bonus = Decimal("20")
            member.repurchase_wallet = Decimal("10")
            member.rank_reward = member.calculate_rank_reward()
            member.save()
            self.members.append(member)

        end_time = time.time()
        self.setup_duration = end_time - start_time

    def test_performance_runtime(self):
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

        print(f"Performance Test: {len(self.members)} members validated successfully")
        print(f"Setup Duration: {self.setup_duration:.2f} seconds")

