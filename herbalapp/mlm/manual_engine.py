# herbalapp/mlm/manual_engine.py
"""
Manual Engine Trigger (Admin/Web safe)

Goal:
- Celery / signals இல்லாமல் Admin button மூலம் engine run செய்ய.
- Duplicate / rerun rules எல்லாம் engine உள்ளே (run_with_lock + EngineLock) already handle செய்கிறது.
  அதனால் இங்கே finished_at / is_running checks போட வேண்டாம்.

This wrapper just calls:
    run_full_daily_engine(run_date)

And returns a user-friendly message for Admin UI.
"""

from __future__ import annotations

from datetime import date as date_cls
from typing import Optional


def run_engine_for_date(run_date: date_cls) -> str:
    """
    Admin/manual run entry point.

    ✅ Uses your production-safe engine: run_full_daily_engine(run_date)
    ✅ EngineLock + rerun rules are enforced inside:
        herbalapp.mlm.final_master_engine.run_full_daily_engine -> run_with_lock(...)

    Returns:
        str message suitable for showing in Django admin messages.
    """
    try:
        # Import inside function to avoid import-time side effects during admin load
        from herbalapp.mlm.final_master_engine import run_full_daily_engine

        run_full_daily_engine(run_date)

        return f"✅ Engine triggered successfully for {run_date}"

    except Exception as e:
        return f"❌ Engine failed for {run_date}. Error: {e}"


# Optional helper (if you want to call from shell quickly)
def run_engine_today() -> str:
    """
    Convenience function for quick testing in Django shell.
    """
    from django.utils import timezone
    return run_engine_for_date(timezone.localdate())

