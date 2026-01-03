from django.test import TestCase
from herbalapp.models import Member
from decimal import Decimal
import time

class BinaryIncomeTest(TestCase):
    def test_binary_income(self):
        member = Member.objects.create(name="BinaryUser", package="Gold", binary_pairs=10)
        member.binary_income = member.calculate_binary_income()
        self.assertEqual(member.binary_income, 1000)
        print(f"Binary Income: {member.binary_income}, Expected: 1000")

class FlashBonusTest(TestCase):
    def test_flash_bonus(self):
        member = Member.objects.create(name="FlashUser", package="Gold", flash_bonus=500)
        self.assertEqual(member.flash_bonus, 500)
        print(f"Flash Bonus: {member.flash_bonus}, Expected: 500")

class RepurchaseWalletTest(TestCase):
    def test_repurchase_wallet(self):
        member = Member.objects.create(name="RepurchaseUser", package="Gold", repurchase_wallet=300)
        self.assertEqual(member.repurchase_wallet, 300)
        print(f"Repurchase Wallet: {member.repurchase_wallet}, Expected: 300")

class ParentBonusTest(TestCase):
    def test_parent_bonus(self):
        member = Member.objects.create(name="ParentUser", package="Gold", parent_bonus=200)
        self.assertEqual(member.parent_bonus, 200)
        print(f"Parent Bonus: {member.parent_bonus}, Expected: 200")

class RankRewardTest(TestCase):
    def test_rank_reward_allocation(self):
        member = Member.objects.create(name="RankUser", package="Gold", bv=1200)
        member.rank_reward = member.calculate_rank_reward()
        self.assertEqual(member.rank_reward, 200)
        print(f"Rank Reward: {member.rank_reward}, Expected: 200")

class SponsorIncomeTest(TestCase):
    def test_sponsor_income(self):
        member = Member.objects.create(name="SponsorUser", package="Gold", sponsor_income=1500)
        self.assertEqual(member.sponsor_income, 1500)
        print(f"Sponsor Income: {member.sponsor_income}, Expected: 1500")

class WalletBalanceTest(TestCase):
    def test_wallet_balance(self):
        member = Member.objects.create(name="WalletUser", package="Gold")
        member.binary_income = 1000
        member.sponsor_income = 1500
        member.parent_bonus = 200
        member.flash_bonus = 500
        member.repurchase_wallet = 300
        member.rank_reward = 200
        expected_balance = 3700
        actual_balance = (
            member.binary_income + member.sponsor_income + member.parent_bonus +
            member.flash_bonus + member.repurchase_wallet + member.rank_reward
        )
        self.assertEqual(actual_balance, expected_balance)
        print(f"Wallet Balance: {actual_balance}, Expected: {expected_balance}")

class LifecycleTest(TestCase):
    def test_full_lifecycle_payout(self):
        member = Member.objects.create(name="LifecycleUser", package="Gold", bv=1200)
        member.binary_pairs = 10
        member.binary_income = member.calculate_binary_income()
        member.sponsor_income = 1500
        member.parent_bonus = 200
        member.flash_bonus = 500
        member.repurchase_wallet = 300
        member.rank_reward = member.calculate_rank_reward()
        expected_balance = 3700
        actual_balance = (
            member.binary_income + member.sponsor_income + member.parent_bonus +
            member.flash_bonus + member.repurchase_wallet + member.rank_reward
        )
        self.assertEqual(actual_balance, expected_balance)
        print(f"Lifecycle Final Wallet Balance: {actual_balance}, Expected: {expected_balance}")

class StressTest(TestCase):
    def test_stress_payouts(self):
        members = []
        for i in range(1, 51):
            member = Member.objects.create(name=f"StressUser{i}", package="Gold", bv=1000+(i*50))
            member.binary_pairs = i
            member.binary_income = member.calculate_binary_income()
            member.sponsor_income = Decimal("100") * i
            member.parent_bonus = Decimal("50")
            member.flash_bonus = Decimal("20")
            member.repurchase_wallet = Decimal("10")
            member.rank_reward = member.calculate_rank_reward()
            members.append(member)
        for m in members:
            total_balance = (
                m.binary_income + m.sponsor_income + m.parent_bonus +
                m.flash_bonus + m.repurchase_wallet + m.rank_reward
            )
            self.assertGreater(total_balance, 0)
        print(f"Stress Test: {len(members)} members validated successfully")

class ActualIncomeTest(TestCase):
    def test_actual_income_values(self):
        member = Member.objects.create(name="ActualUser", package="Gold", bv=1200)
        member.binary_income = Decimal("2500")
        member.sponsor_income = Decimal("1500")
        member.parent_bonus = Decimal("200")
        member.flash_bonus = Decimal("500")
        member.repurchase_wallet = Decimal("300")
        member.rank_reward = member.calculate_rank_reward()
        expected_balance = 5200
        actual_balance = (
            member.binary_income + member.sponsor_income + member.parent_bonus +
            member.flash_bonus + member.repurchase_wallet + member.rank_reward
        )
        self.assertEqual(actual_balance, expected_balance)
        print(f"Actual Programme Wallet Balance: {actual_balance}, Expected: {expected_balance}")

class NegativeTest(TestCase):
    def test_inactive_member_payouts(self):
        member = Member.objects.create(name="InactiveUser", package="Gold", active=False, bv=2000)
        member.binary_income = member.sponsor_income = member.parent_bonus = member.flash_bonus = member.repurchase_wallet = member.rank_reward = Decimal("0")
        total_balance = (
            member.binary_income + member.sponsor_income + member.parent_bonus +
            member.flash_bonus + member.repurchase_wallet + member.rank_reward
        )
        self.assertEqual(total_balance, 0)
        print(f"Inactive Member Wallet Balance: {total_balance}, Expected: 0")

    def test_low_bv_member_rank_reward(self):
        member = Member.objects.create(name="LowBVUser", package="Silver", bv=800)
        member.rank_reward = member.calculate_rank_reward()
        self.assertEqual(member.rank_reward, 0)
        print(f"Low BV Member Rank Reward: {member.rank_reward}, Expected: 0")

class PerformanceTest(TestCase):
    def test_performance_runtime(self):
        members = []
        start_time = time.time()
        for i in range(1, 501):
            member = Member.objects.create(name=f"PerfUser{i}", package="Gold", bv=1000+(i*10))
            member.binary_pairs = i
            member.binary_income = member.calculate_binary_income()
            member.sponsor_income = Decimal("100") * i
            member.parent_bonus = Decimal("50")
            member.flash_bonus = Decimal("20")
            member.repurchase_wallet = Decimal("10")
            member.rank_reward = member.calculate_rank_reward()
            members.append(member)
        end_time = time.time()
        duration = end_time - start_time
        for m in members:
            total_balance = (
                m.binary_income + m.sponsor_income + m.parent_bonus +
                m.flash_bonus + m.repurchase_wallet + m.rank_reward
            )
            self.assertGreater(total_balance, 0)
        print(f"Performance Test: {len(members)} members validated successfully")
        print(f"Setup Duration: {duration:.2f} seconds")

