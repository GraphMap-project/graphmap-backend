from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class EndpointMetrics(SQLModel, table=True):
    """Агреговані метрики по унікальних ендпоінтах"""

    __tablename__ = "endpoint_metrics"

    id: Optional[int] = Field(default=None, primary_key=True)
    endpoint: str = Field(index=True)
    method: str = Field(default="GET")  # HTTP метод
    algorithm: Optional[str] = Field(
        default=None, index=True
    )  # Алгоритм, якщо застосовно

    # Статистика часу відповіді
    total_requests: int = Field(default=0)
    avg_response_time_ms: float = Field(default=0.0)
    min_response_time_ms: float = Field(default=0.0)
    max_response_time_ms: float = Field(default=0.0)

    last_request_time_ms: float = Field(default=0.0)

    # Статистика помилок
    error_count: int = Field(default=0)
    success_rate_percent: float = Field(default=100.0)

    # Часові мітки
    first_request_at: datetime = Field(default_factory=datetime.utcnow)
    last_request_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("endpoint", "algorithm", name="uix_endpoint_algorithm"),
    )
