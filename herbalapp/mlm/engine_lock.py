from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from herbalapp.models import EngineLock


def run_with_lock(run_date, engine_func):
    """
    Global MLM Engine Lock

    ✅ Prevents double execution
    ✅ Auto-recovers from crashed / stuck engines
    ✅ Celery-safe
    """

    with transaction.atomic():
        lock, created = EngineLock.objects.select_for_update().get_or_create(
            run_date=run_date
        )

        # -----------------------------
        # 🛑 Already running check
        # -----------------------------
        if lock.is_running:
            # 🔧 SAFETY: auto-release stale lock (10 mins)
            if lock.started_at and timezone.now() - lock.started_at > timedelta(minutes=10):
                lock.is_running = False
                lock.started_at = None
                lock.save()
            else:
                print("⛔ Engine already running — skipped")
                return

        # -----------------------------
        # ✅ Acquire lock
        # -----------------------------
        lock.is_running = True
        lock.started_at = timezone.now()
        lock.save()

    try:
        engine_func(run_date)

    finally:
        # -----------------------------
        # 🔓 Always release lock safely
        # -----------------------------
        with transaction.atomic():
            fresh_lock = EngineLock.objects.select_for_update().get(
                run_date=run_date
            )
            fresh_lock.is_running = False
            fresh_lock.started_at = None
            fresh_lock.save()

