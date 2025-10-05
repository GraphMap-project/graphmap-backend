from typing import List

from pydantic import BaseModel, Field


class RouteSave(BaseModel):
    route_id: str = Field(..., description="Temporary route ID from cache")
    name: str = Field(..., min_length=1, max_length=100, description="Route name")
