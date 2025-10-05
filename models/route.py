import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import JSON, Field, Relationship, SQLModel


class Route(SQLModel, table=True):
    # Primary identifiers
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)

    # Route metadata
    algorithm: str = Field(index=True)
    total_distance: float

    # Route data
    route_coords: List[List[float]] = Field(sa_column=Column(JSONB))
    full_route_nodes: List[int] = Field(sa_column=Column(JSONB))

    #  Start/End points for quick reference
    start_point: List[float] = Field(sa_column=Column(JSONB))
    end_point: List[float] = Field(sa_column=Column(JSONB))
    intermediate_points: Optional[List[List[float]]] = Field(
        default=None, sa_column=Column(JSONB)
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, nullable=False, index=True
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow}
    )

    # User relationship
    user_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="user.id", index=True
    )
