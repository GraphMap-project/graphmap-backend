import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel


class Threat(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    type: str = Field(index=True, nullable=True)
    description: str = Field(nullable=True)
    location: list[dict] = Field(sa_column=Column(JSONB))
    created_by: str | None = Field(default=None, index=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow, nullable=False)
