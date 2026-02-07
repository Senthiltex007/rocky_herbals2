# herbalapp/mlm/engine_lock.py

from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from herbalapp.models import EngineLock


def run_with_lock(run_date, engine_func, allow_rerun_today=True, cooldown_minutes=5):
    """
    ✅ Global MLM Engine Lock (MODEL-MATCHED)

    - Prevents parallel execution using is_running
    - Uses finished_at for completion
    - Allows rerun ONLY for TODAY with cooldown (late joins fix)
    """

    now = timezone.now()
    today = timezone.localdate()

    with transaction.atomic():
        lock, _ = EngineLock.objects.select_for_update().get_or_create(run_date=run_date)

        # -----------------------------
        # 🛑 Already running check
        # -----------------------------
        if lock.is_running:
            # auto-release stale lock (10 mins)
            if lock.started_at and now - lock.started_at > timedelta(minutes=10):
                lock.is_running = False
                lock.started_at = None
                lock.save(update_fields=["is_running", "started_at"])
            else:
                print("⛔ Engine already running — skipped")
                return

        # -----------------------------
        # ✅ Finished check (rerun policy)
        # -----------------------------
        if lock.finished_at:
            # Past dates -> never auto rerun
            if run_date != today:
                print(f"⛔ Engine already finished for {run_date} — skipped")
                return

            # Today -> allow rerun only if enabled
            if not allow_rerun_today:
                print(f"⛔ Today rerun disabled for {run_date} — skipped")
                return

            # Cooldown based on last finished time
            if now - lock.finished_at < timedelta(minutes=cooldown_minutes):
                print(f"⏳ Cooldown active ({cooldown_minutes}m) — skipped")
                return

        # -----------------------------
        # ✅ Acquire lock
        # -----------------------------
        lock.is_running = True
        lock.started_at = now
        lock.save(update_fields=["is_running", "started_at"])

    try:
        engine_func(run_date)

        # ✅ Mark finished on success
        with transaction.atomic():
            fresh_lock = EngineLock.objects.select_for_update().get(run_date=run_date)
            fresh_lock.is_running = False
            fresh_lock.started_at = None
            fresh_lock.finished_at = timezone.now()
            fresh_lock.save(update_fields=["is_running", "started_at", "finished_at"])

    finally:
        # 🔓 Always release lock even if crash (do not touch finished_at)
        try:
            with transaction.atomic():
                fresh_lock = EngineLock.objects.select_for_update().get(run_date=run_date)
                if fresh_lock.is_running:
                    fresh_lock.is_running = False
                    fresh_lock.started_at = None
                    fresh_lock.save(update_fields=["is_running", "started_at"])
        except EngineLock.DoesNotExist:
            pass

