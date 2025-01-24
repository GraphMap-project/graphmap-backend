from fastapi import APIRouter, HTTPException

from config.database import SessionDep
from models.user import User
from schemas.userCreate import UserCreate

account = APIRouter()


@account.post("/register")
def register(user: UserCreate, session: SessionDep):
    new_user = User(name=user.name, email=user.email, password=user.password)

    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return {"message": "created successfully"}
