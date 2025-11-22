import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel


class RequestAction(str, Enum):
    CREATE = "create"
    DELETE = "delete"


class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


class ThreatRequest(SQLModel, table=True):
    __tablename__ = "threat_request"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    action: RequestAction = Field(index=True)
    status: RequestStatus = Field(default=RequestStatus.PENDING, index=True)

    # Threat data for CREATE requests
    threat_type: str | None = Field(default=None)
    description: str | None = Field(default=None)
    location: list[dict] | None = Field(default=None, sa_column=Column(JSONB))

    # Reference for DELETE requests
    threat_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey(
            "threat.id", ondelete="CASCADE"), nullable=True),
    )

    # Tracking
    requested_by: uuid.UUID = Field(foreign_key="user.id", index=True)
    reviewed_by: uuid.UUID | None = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, nullable=False)
    reviewed_at: datetime | None = Field(default=None)
