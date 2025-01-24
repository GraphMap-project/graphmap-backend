from fastapi import APIRouter, HTTPException

from config.database import SessionDep
from models.user import User
from schemas.userCreate import UserCreate

account = APIRouter()


@account.post("/register")
def register(user: UserCreate, session: SessionDep):
    existing_user = session.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")
    new_user = User(email=user.email, password=user.password)

    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return {"message": "created successfully"}
