# herbalapp/tasks.py

from celery import shared_task
from datetime import date
from herbalapp.models import Member
from herbalapp.mlm.final_master_engine import run_full_daily_engine

@shared_task
def update_income_task(member_auto_id):
    """
    Celery task to update income for a member.
    This task no longer duplicates engine logic.
    It calls the production-ready MLM engine.
    """

    try:
        # 🔹 Get the member object (just for logging)
        member = Member.objects.get(auto_id=member_auto_id)
        run_date = date.today()

        print(f"🚀 Triggered MLM Engine for all members by {member.auto_id}")

        # 🔹 Call the real engine for today
        run_full_daily_engine(run_date)

        return f"✅ Income update completed for {member_auto_id}"

    except Member.DoesNotExist:
        return f"❌ Member {member_auto_id} does not exist"

    except Exception as e:
        return f"❌ Failed to update income for {member_auto_id}: {e}"

