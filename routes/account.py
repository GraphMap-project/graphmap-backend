from schemas.userCreate import UserCreate
from models.user import User
from fastapi import APIRouter, HTTPException
from config.database import SessionDep

account = APIRouter()


@account.post("/register")
def register(user: User, session: SessionDep) -> User:
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"message": "created successfully"}
