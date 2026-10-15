from pydantic import BaseModel, ConfigDict, Field


class PriceTickRead(BaseModel):
    id: int
    ticker: str
    price: float
    timestamp: int = Field(description="UNIX timestamp in seconds")

    model_config = ConfigDict(from_attributes=True)


class LatestPriceRead(BaseModel):
    ticker: str
    price: float
    timestamp: int = Field(description="UNIX timestamp in seconds")
