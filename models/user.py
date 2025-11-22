import uuid
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: Optional[str]
    email: str
    password: str
    role: str = Field(default="threat-responsible")
    status: str = Field(default="active")
    disabled_reason: Optional[str] = Field(default=None)
    disabled_at: Optional[str] = Field(default=None)

    routes: List["Route"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
