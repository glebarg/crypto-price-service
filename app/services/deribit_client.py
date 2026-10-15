import asyncio
import logging
from dataclasses import dataclass

import aiohttp

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ExchangeClientError(RuntimeError):
    """Raised when the exchange response cannot provide a valid price."""


@dataclass(frozen=True, slots=True)
class IndexPrice:
    ticker: str
    price: float


class DeribitClient:
    """Small async HTTP client for Deribit's public index-price endpoint."""

    def __init__(self, base_url: str | None = None, timeout_seconds: float | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.deribit_api_base).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.request_timeout_seconds

    async def get_index_price(self, ticker: str) -> IndexPrice:
        url = f"{self.base_url}/public/get_index_price"
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params={"index_name": ticker}) as response:
                    response.raise_for_status()
                    payload = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            raise ExchangeClientError(f"Failed to fetch {ticker} from Deribit: {exc}") from exc

        try:
            result = payload["result"]
            price = float(result["index_price"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ExchangeClientError(f"Unexpected Deribit response for {ticker}") from exc

        if price <= 0:
            raise ExchangeClientError(f"Deribit returned a non-positive price for {ticker}")
        return IndexPrice(ticker=ticker, price=price)
