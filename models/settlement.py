from sqlmodel import Field, SQLModel


class Settlement(SQLModel, table=True):
    __tablename__ = "settlements"

    id: int = Field(default=None, primary_key=True)
    geoname_id: int = Field(index=True, unique=True)
    name: str
    type: str
    lat: float
    lon: float
    country: str = "UA"
