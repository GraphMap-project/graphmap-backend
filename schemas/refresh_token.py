from pydantic import BaseModel


class RefreshToken(BaseModel):
    token: str
