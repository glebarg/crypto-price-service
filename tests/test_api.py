from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.repositories.prices import PriceRepository


def test_api_endpoints():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestingSession() as db:
        PriceRepository(db).add("btc_usd", 64000.25, 1_700_000_000)
        PriceRepository(db).add("btc_usd", 64100.25, 1_700_000_060)
        db.commit()

    try:
        with TestClient(app) as client:
            response = client.get("/api/prices", params={"ticker": "btc_usd"})
            assert response.status_code == 200
            assert len(response.json()) == 2

            page = client.get("/api/prices", params={"ticker": "btc_usd", "limit": 1, "offset": 1})
            assert page.status_code == 200
            assert len(page.json()) == 1
            assert page.json()[0]["timestamp"] == 1_700_000_060

            response = client.get("/api/prices/latest", params={"ticker": "btc_usd"})
            assert response.status_code == 200
            assert response.json()["price"] == 64100.25

            response = client.get(
                "/api/prices/filter",
                params={"ticker": "btc_usd", "date_from": "2023-11-14T22:14:00Z"},
            )
            assert response.status_code == 200
            assert len(response.json()) == 1

            assert client.get("/api/prices", params={"ticker": "bad"}).status_code == 422
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
