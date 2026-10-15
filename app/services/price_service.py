import logging
import time

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.prices import PriceRepository, SUPPORTED_TICKERS
from app.services.deribit_client import DeribitClient, ExchangeClientError

logger = logging.getLogger(__name__)


class PriceService:
    def __init__(self, session: Session, client: DeribitClient | None = None) -> None:
        self.repository = PriceRepository(session)
        self.session = session
        self.client = client or DeribitClient()

    def validate_ticker(self, ticker: str) -> str:
        normalized = ticker.strip().lower()
        if normalized not in SUPPORTED_TICKERS:
            raise ValueError(f"Unsupported ticker '{ticker}'. Supported tickers: {', '.join(sorted(SUPPORTED_TICKERS))}")
        return normalized

    async def collect_one(self, ticker: str) -> None:
        ticker = self.validate_ticker(ticker)
        index_price = await self.client.get_index_price(ticker)
        timestamp = int(time.time())
        try:
            self.repository.add(index_price.ticker, index_price.price, timestamp)
            # This method owns its transaction so it is safe to call independently.
            self.session.commit()
        except IntegrityError:
            # A ticker can only have one row per second. Repeated collection is idempotent.
            self.session.rollback()
            logger.info("Duplicate price tick skipped for %s at %s", ticker, timestamp)

    async def collect_all(self) -> dict[str, str]:
        """Collect each ticker independently so one upstream failure won't skip the other."""
        results: dict[str, str] = {}
        for ticker in sorted(SUPPORTED_TICKERS):
            try:
                await self.collect_one(ticker)
                results[ticker] = "saved"
            except (ExchangeClientError, ValueError) as exc:
                self.session.rollback()
                logger.exception("Could not collect %s", ticker)
                results[ticker] = f"error: {exc}"
            except Exception:
                self.session.rollback()
                logger.exception("Unexpected error while collecting %s", ticker)
                results[ticker] = "error: unexpected error"
        return results
