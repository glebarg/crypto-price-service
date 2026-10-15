import asyncio
import logging

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.price_service import PriceService

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.price_tasks.collect_prices", autoretry_for=(), ignore_result=False)
def collect_prices() -> dict[str, str]:
    """Celery task entry point; asyncio is contained inside the synchronous task."""
    db = SessionLocal()
    try:
        result = asyncio.run(PriceService(db).collect_all())
        logger.info("Price collection completed: %s", result)
        return result
    finally:
        db.close()
