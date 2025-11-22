from typing import List

from pydantic import BaseModel


class LocationWithName(BaseModel):
    lat: float
    lng: float
    name: str


class ThreatRequestCreate(BaseModel):
    type: str
    description: str
    location: List[LocationWithName]
