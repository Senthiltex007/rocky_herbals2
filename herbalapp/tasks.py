from celery import shared_task
from datetime import date
from django.utils.dateparse import parse_date
from django.utils import timezone
from herbalapp.mlm.final_master_engine import run_full_daily_engine

@shared_task
def run_daily_engine_task(run_date_str=None):
    # beat args இல்லாமலும், args இருந்தாலும் work ஆகணும்
    if run_date_str:
        run_date = parse_date(run_date_str)
    else:
        run_date = timezone.localdate()

    run_full_daily_engine(run_date)
    return f"OK: MLM engine ran for {run_date}"

