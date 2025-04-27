from typing import List, Literal, Optional

from pydantic import BaseModel, conlist


class RouteRequest(BaseModel):
    algorithm: Literal["dijkstra", "alt"]
    start_point: conlist(float, min_length=2, max_length=2)
    end_point: conlist(float, min_length=2, max_length=2)
    intermediate_points: Optional[List[conlist(
        float, min_length=2, max_length=2)]] = []
    threats: Optional[List[List[conlist(float, min_length=2, max_length=2)]]] = [
    ]

    def __len__(self):
        point_lst = [self.start_point,
                     self.end_point, self.intermediate_points]
        return len(point_lst)
