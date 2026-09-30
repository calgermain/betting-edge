from datetime import datetime
from pydantic import BaseModel, Field

class Outcome(BaseModel):
    name: str
    price: int | float
    point: float | None = None
    description: str | None = None

class Market(BaseModel):
    key: str
    last_update: datetime | None = None
    outcomes: list[Outcome] = Field(default_factory=list)

class Bookmaker(BaseModel):
    key: str
    title: str
    last_update: datetime | None = None
    markets: list[Market] = Field(default_factory=list)

class NormalizedEventOdds(BaseModel):
    id: str
    sport_key: str
    sport_title: str
    commence_time: datetime
    home_team: str
    away_team: str
    bookmakers: list[Bookmaker] = Field(default_factory=list)
    source: str = "the-odds-api"
