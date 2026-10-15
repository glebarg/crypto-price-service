from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "crypto_price_service",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.price_tasks"],
)
celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "collect-crypto-prices-every-minute": {
            "task": "app.tasks.price_tasks.collect_prices",
            "schedule": 60.0,
            # Do not execute a stale queued collection task after a long worker outage.
            "options": {"expires": 55},
        }
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
