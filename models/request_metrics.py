from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class RequestMetrics(SQLModel, table=True):
    """Model to store metrics about API requests."""

    __tablename__ = "request_metrics"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    endpoint: str = Field(index=True)
    method: str
    response_time_ms: float
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
