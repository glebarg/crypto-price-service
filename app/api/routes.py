from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import valid_ticker
from app.api.dependencies import db_session
from app.repositories.prices import PriceRepository
from app.schemas.price import LatestPriceRead, PriceTickRead

router = APIRouter(prefix="/api/prices", tags=["prices"])


def to_unix(value: datetime | None, name: str) -> int | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp())


@router.get("", response_model=list[PriceTickRead], summary="Get all saved prices for a ticker")
def get_prices(
    ticker: str = Depends(valid_ticker),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum number of records (1–500)"),
    offset: int = Query(default=0, ge=0, description="Number of records to skip"),
    db: Session = Depends(db_session),
) -> list[PriceTickRead]:
    return PriceRepository(db).list_for_ticker(ticker, limit=limit, offset=offset)


@router.get("/latest", response_model=LatestPriceRead, summary="Get the latest saved price")
def get_latest_price(
    ticker: str = Depends(valid_ticker), db: Session = Depends(db_session)
) -> LatestPriceRead:
    tick = PriceRepository(db).latest(ticker)
    if tick is None:
        raise HTTPException(status_code=404, detail=f"No saved prices for ticker '{ticker}'")
    return LatestPriceRead(ticker=tick.ticker, price=float(tick.price), timestamp=tick.timestamp)


@router.get("/filter", response_model=list[PriceTickRead], summary="Filter prices by date/time")
def get_filtered_prices(
    ticker: str = Depends(valid_ticker),
    date_from: datetime | None = Query(default=None, description="ISO 8601 datetime, inclusive"),
    date_to: datetime | None = Query(default=None, description="ISO 8601 datetime, inclusive"),
    db: Session = Depends(db_session),
) -> list[PriceTickRead]:
    start = to_unix(date_from, "date_from")
    end = to_unix(date_to, "date_to")
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=422, detail="date_from must be earlier than or equal to date_to")
    rows = PriceRepository(db).filter_by_timestamp(ticker, start, end)
    return rows
