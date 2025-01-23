from sqlmodel import Session, SQLModel, create_engine
from typing import Annotated
from fastapi import Depends

DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/graphmap"

engine = create_engine(DATABASE_URL, echo=True)


# Создание таблиц в базе данных
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# Получение сессии базы данных
def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
