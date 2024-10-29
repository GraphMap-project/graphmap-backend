from typing import List

from pydantic import BaseModel, conlist


class RouteRequest(BaseModel):
    start_point: conlist(float, min_length=2, max_length=2)
    end_point: conlist(float, min_length=2, max_length=2)
