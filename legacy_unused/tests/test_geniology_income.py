from django.test import TestCase
from django.utils import timezone
from herbalapp.models import Member

class GeniologyIncomeTests(TestCase):
    def setUp(self):
        # Common sponsor for all tests
        self.sponsor = Member.objects.create(
            name="Sponsor",
            package="Gold"
        )

    def test_sponsor_income_basic(self):
        """Sponsor income duplication from two children"""
        child1 = Member.objects.create(name="Child1", sponsor=self.sponsor, package="Gold", binary_pairs=5)
        child2 = Member.objects.create(name="Child2", sponsor=self.sponsor, package="Silver", binary_pairs=10)

        child1.binary_income = child1.calculate_binary_income()
        child1.save(update_fields=["binary_income"])
        child2.binary_income = child2.calculate_binary_income()
        child2.save(update_fields=["binary_income"])

        expected_income = child1.calculate_binary_income() + child2.calculate_binary_income()
        sponsor_income = self.sponsor.calculate_sponsor_income()

        self.assertEqual(sponsor_income, expected_income)
        print(f"[Sponsor Income Basic] {sponsor_income} == {expected_income}")

    def test_sponsor_income_stress(self):
        """Sponsor income scaling with 50 children"""
        children = []
        for i in range(50):
            c = Member.objects.create(name=f"Child{i+1}", sponsor=self.sponsor, package="Gold", binary_pairs=i+1)
            c.binary_income = c.calculate_binary_income()
            c.save(update_fields=["binary_income"])
            children.append(c)

        expected_income = sum(c.calculate_binary_income() for c in children)
        sponsor_income = self.sponsor.calculate_sponsor_income()

        self.assertEqual(sponsor_income, expected_income)
        print(f"[Sponsor Income Stress] {sponsor_income} == {expected_income}")

    def test_daily_cutoff_income(self):
        """Only today's new members contribute to income"""
        # Today’s children
        for i in range(10):
            Member.objects.create(name=f"ChildToday{i+1}", sponsor=self.sponsor,
                                  package="Gold", binary_pairs=2, joined_date=timezone.now().date())
        # Yesterday’s children
        yesterday = timezone.now().date() - timezone.timedelta(days=1)
        for i in range(5):
            Member.objects.create(name=f"ChildYesterday{i+1}", sponsor=self.sponsor,
                                  package="Gold", binary_pairs=3, joined_date=yesterday)

        income_data = self.sponsor.calculate_full_income()
        new_members_today = self.sponsor.get_new_members_today_count()

        self.assertEqual(new_members_today, 10)
        print(f"[Daily Cutoff] New={new_members_today}, Binary={income_data['binary_income']}, Flash={income_data['flash_bonus']}")

    def test_flash_bonus_and_washout(self):
        """Overflow pairs generate flash bonus and washout members"""
        for i in range(30):
            Member.objects.create(name=f"Child{i+1}", sponsor=self.sponsor,
                                  package="Gold", joined_date=timezone.now().date())

        income_data = self.sponsor.calculate_full_income()
        new_members_today = self.sponsor.get_new_members_today_count()

        self.assertEqual(new_members_today, 30)
        print(f"[Flash Bonus] New={new_members_today}, Binary={income_data['binary_income']}, Flash={income_data['flash_bonus']}, Washout={income_data['wash_out_members']}")

        """Salary slabs based on BV thresholds"""
    # paste here
def test_salary_slabs(self):
        """Salary slabs based on BV thresholds"""
        left_child = Member.objects.create(..., bv=300000)
        right_child = Member.objects.create(..., bv=300000)
        # Create left/right subtrees with enough depth to generate BV
        left_child = Member.objects.create(name="LeftChild", sponsor=self.sponsor, package="Gold")
        right_child = Member.objects.create(name="RightChild", sponsor=self.sponsor, package="Gold")
        self.sponsor.left_child = left_child
        self.sponsor.right_child = right_child
        self.sponsor.save()

        # Add more descendants to boost BV
        for i in range(50):
            Member.objects.create(name=f"L{i}", sponsor=left_child, package="Gold", joined_date=timezone.now().date())
            Member.objects.create(name=f"R{i}", sponsor=right_child, package="Gold", joined_date=timezone.now().date())

        income_data = self.sponsor.calculate_full_income()
        print(f"[Salary Slab] Salary={income_data['salary']}, BV Left/Right={self.sponsor.get_bv_counts()}")

        # Expect salary >= 10000 when BV thresholds are met
        self.assertTrue(income_data["salary"] >= 10000)

        # Force BV values
        left_child.bv = 300000
        right_child.bv = 300000
        left_child.save(update_fields=["bv"])
        right_child.save(update_fields=["bv"])

        income_data = self.sponsor.calculate_full_income()
        self.assertTrue(income_data["salary"] >= 10000)
        print(f"[Salary Slab] Salary={income_data['salary']}, BV Left/Right OK")

