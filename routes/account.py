from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import select

from config.database import SessionDep
from config.jwt_config import *
from models.user import User
from schemas.userCreate import UserCreate
from schemas.userLogin import UserLogin

account = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@account.post("/register")
def register(user: UserCreate, session: SessionDep):
    statement = select(User).where(User.email == user.email)
    existing_user = session.exec(statement).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    hashed_password = hash_password(user.password)

    new_user = User(email=user.email, password=hashed_password)

    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return {"message": "created successfully"}


@account.post("/login")
def login(user: UserLogin, session: SessionDep):
    statement = select(User).where(User.email == user.email)
    db_user = session.exec(statement).first()
    if not db_user:
        raise HTTPException(
            status_code=401, detail="There is no user with such email")
    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}
