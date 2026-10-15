import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.repositories.prices import PriceRepository
from app.services.deribit_client import ExchangeClientError, IndexPrice
from app.services.price_service import PriceService


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def test_repository_saves_and_returns_prices(session):
    repository = PriceRepository(session)
    repository.add("btc_usd", 65000.5, 100)
    repository.add("btc_usd", 65100.5, 160)
    repository.add("eth_usd", 3200.0, 160)
    session.commit()

    assert len(repository.list_for_ticker("btc_usd")) == 2
    assert float(repository.latest("btc_usd").price) == 65100.5
    assert [row.timestamp for row in repository.filter_by_timestamp("btc_usd", 120, 170)] == [160]


def test_validate_ticker_rejects_unknown_symbol(session):
    service = PriceService(session, client=SimpleNamespace())
    with pytest.raises(ValueError, match="Unsupported ticker"):
        service.validate_ticker("doge_usd")


def test_collect_all_saves_success_and_continues_after_failure(session):
    client = SimpleNamespace(get_index_price=AsyncMock(side_effect=[
        IndexPrice("btc_usd", 65000.0),
        ExchangeClientError("upstream unavailable"),
    ]))
    result = asyncio.run(PriceService(session, client=client).collect_all())

    assert result["btc_usd"] == "saved"
    assert result["eth_usd"].startswith("error:")
    assert len(PriceRepository(session).list_for_ticker("btc_usd")) == 1
    assert PriceRepository(session).list_for_ticker("eth_usd") == []


def test_duplicate_ticker_timestamp_is_rejected(session):
    repository = PriceRepository(session)
    repository.add("btc_usd", 65000.0, 100)
    session.commit()

    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        repository.add("btc_usd", 65100.0, 100)
    session.rollback()

    assert len(repository.list_for_ticker("btc_usd")) == 1
