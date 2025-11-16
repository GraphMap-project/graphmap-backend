from typing import List

from pydantic import BaseModel


class ThreatRequestCreate(BaseModel):
    type: str
    description: str
    location: List[List[float]]
