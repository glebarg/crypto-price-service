from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.prices import SUPPORTED_TICKERS


def valid_ticker(ticker: str = Query(..., description="Supported values: btc_usd, eth_usd")) -> str:
    normalized = ticker.strip().lower()
    if normalized not in SUPPORTED_TICKERS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported ticker. Supported values: {', '.join(sorted(SUPPORTED_TICKERS))}",
        )
    return normalized


def db_session(db: Session = Depends(get_db)) -> Session:
    return db
