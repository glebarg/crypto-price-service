from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.price_tick import PriceTick

SUPPORTED_TICKERS = frozenset({"btc_usd", "eth_usd"})


class PriceRepository:
    """Database access for price history; transaction boundaries stay in the service."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, ticker: str, price: float, timestamp: int) -> PriceTick:
        tick = PriceTick(ticker=ticker, price=price, timestamp=timestamp)
        self.session.add(tick)
        self.session.flush()
        return tick

    def list_for_ticker(
        self, ticker: str, limit: int = 100, offset: int = 0
    ) -> list[PriceTick]:
        query: Select[tuple[PriceTick]] = (
            select(PriceTick)
            .where(PriceTick.ticker == ticker)
            .order_by(PriceTick.timestamp.asc(), PriceTick.id.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(query).all())

    def latest(self, ticker: str) -> PriceTick | None:
        query = (
            select(PriceTick)
            .where(PriceTick.ticker == ticker)
            .order_by(PriceTick.timestamp.desc(), PriceTick.id.desc())
            .limit(1)
        )
        return self.session.scalar(query)

    def filter_by_timestamp(
        self, ticker: str, date_from: int | None, date_to: int | None
    ) -> list[PriceTick]:
        query = select(PriceTick).where(PriceTick.ticker == ticker)
        if date_from is not None:
            query = query.where(PriceTick.timestamp >= date_from)
        if date_to is not None:
            query = query.where(PriceTick.timestamp <= date_to)
        query = query.order_by(PriceTick.timestamp.asc(), PriceTick.id.asc())
        return list(self.session.scalars(query).all())
