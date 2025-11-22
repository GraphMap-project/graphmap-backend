import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class LoginActivity(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(index=True)
    ip: str
    country: str
    city: str
    latitude: float
    longitude: float
    user_agent: str
    login_time: datetime = Field(default_factory=datetime.utcnow)
    risk_score: int = Field(default=0)
    triggered_rules: dict | None = Field(default=None)
