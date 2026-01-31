from django.utils import timezone
from celery import shared_task

# ❌ FINAL ENGINE IMPORT REMOVE
# from herbalapp.mlm.final_master_engine import run_full_daily_engine
# from herbalapp.mlm.engine_lock import run_with_lock

#from herbalapp.mlm.preview_engine import run_preview_engine

# ----------------------------------------------------------
# Celery Task: PREVIEW ONLY (SAFE)
# ----------------------------------------------------------
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=5,
    retry_kwargs={"max_retries": 3},
)
def run_engine_task(self):
    """
    ⚠️ PREVIEW ONLY
    - Binary preview
    - No sponsor
    - No total lock
    """
    run_preview_engine(timezone.localdate())

