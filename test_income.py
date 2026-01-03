import os
import django
from decimal import Decimal
from django.utils import timezone

# ================= Django Setup =================
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rocky_herbals2.settings')
django.setup()

from herbalapp.models import Member, DailyIncomeReport
from herbalapp.utils.binary_income import process_member_binary_income

# ================== Test Members ==================
def create_test_members():
    # Parent member (already eligible)
    parent, _ = Member.objects.get_or_create(
        member_id="rocky001",
        defaults={
            'name': 'Parent User',
            'phone': '9999000000',
            'email': 'parent@example.com',
            'binary_eligible': True,
            'binary_eligible_date': timezone.now(),
        }
    )

    # Child members under left & right
    left_child, _ = Member.objects.get_or_create(
        member_id="rocky002",
        defaults={
            'name': 'Left Child',
            'phone': '9999000001',
            'email': 'left@example.com',
            'parent': parent,
            'sponsor': parent,
        }
    )
    right_child, _ = Member.objects.get_or_create(
        member_id="rocky003",
        defaults={
            'name': 'Right Child',
            'phone': '9999000002',
            'email': 'right@example.com',
            'parent': parent,
            'sponsor': parent,
        }
    )

    # Update parent's left_new_today / right_new_today to simulate new join
    parent.left_new_today = 1
    parent.right_new_today = 2
    parent.save(update_fields=['left_new_today', 'right_new_today'])

    return parent, left_child, right_child

# ================== Run Binary & Sponsor Income ==================
def run_test():
    parent, left_child, right_child = create_test_members()

    print("Before processing:")
    print("Parent total sponsor income:", parent.total_sponsor_income)

    # Trigger binary income processing
    income = process_member_binary_income(parent)
    print("Binary income credited today:", income)

    # Reload parent from DB
    parent.refresh_from_db()
    print("After processing:")
    print("Parent total sponsor income:", parent.total_sponsor_income)

    # Check DailyIncomeReport
    today = timezone.now().date()
    report = DailyIncomeReport.objects.filter(member=parent, date=today).first()
    if report:
        print("Daily Report:", report.binary_income, report.sponsor_income)
    else:
        print("No DailyIncomeReport found.")

if __name__ == "__main__":
    run_test()

