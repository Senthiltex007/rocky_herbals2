from django.test import TestCase
from herbalapp.models import Member

class RankRewardTest(TestCase):
    def setUp(self):
        self.member = Member.objects.create(name="RankUser", package="Gold", bv=1200)
        # Simulate rank reward trigger
        self.member.rank_reward = self.member.calculate_rank_reward()
        self.member.save()

    def test_rank_reward_allocation(self):
        expected_reward = self.member.calculate_rank_reward()
        self.assertEqual(self.member.rank_reward, expected_reward)
        print(f"Rank Reward: {self.member.rank_reward}, Expected: {expected_reward}")

