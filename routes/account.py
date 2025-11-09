from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi_mail import FastMail, MessageSchema, MessageType
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import select

from config.database import SessionDep
from config.jwt_config import *
from config.mail import EMAIL_CONFIG, FRONTEND_URL
from models.user import User
from schemas.reset_password import PasswordResetConfirm, PasswordResetRequest
from schemas.userCreate import UserCreate
from schemas.userLogin import UserLogin

account = APIRouter(prefix="/account")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/account/login")
refresh_token_scheme = OAuth2PasswordBearer(tokenUrl="/account/refresh")


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


def create_refresh_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, REFRESH_TOKEN_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(session: SessionDep, token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    stmt = select(User).where(User.email == email)
    user = session.exec(stmt).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def create_password_reset_token(email: str):
    """Create a token for password reset that expires in 15 minutes"""
    expires_delta = timedelta(minutes=15)
    to_encode = {"sub": email, "type": "password_reset"}
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def send_password_reset_email(email: str, token: str):
    """Send password reset email with token"""
    reset_link = f"{FRONTEND_URL}/reset-password?token={token}"

    html_content = f"""
    <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>You requested to reset your password. Click the link below to reset it:</p>
            <p><a href="{reset_link}">Reset Password</a></p>
            <p>This link will expire in 15 minutes.</p>
            <p>If you didn't request this, please ignore this email.</p>
        </body>
    </html>
    """

    message = MessageSchema(
        subject="Password Reset Request",
        recipients=[email],
        body=html_content,
        subtype=MessageType.html,
    )

    fm = FastMail(EMAIL_CONFIG)
    await fm.send_message(message)


@account.post("/register")
def register(user: UserCreate, session: SessionDep):
    statement = select(User).where(User.email == user.email)
    existing_user = session.exec(statement).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    hashed_password = hash_password(user.password)

    new_user = User(email=user.email, password=hashed_password, role=user.role)

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": new_user.email}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": new_user.email}, expires_delta=refresh_token_expires
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


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
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": db_user.email}, expires_delta=refresh_token_expires
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@account.post("/refresh")
def refresh_access_token(
    session: SessionDep, token: str = Depends(refresh_token_scheme)
):
    try:
        payload = jwt.decode(
            token, REFRESH_TOKEN_SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if email is None:
            raise HTTPException(
                status_code=401, detail="Invalid refresh token")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    stmt = select(User).where(User.email == email)
    user = session.exec(stmt).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)

    new_access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    new_refresh_token = create_refresh_token(
        data={"sub": user.email}, expires_delta=refresh_token_expires
    )

    return {"access_token": new_access_token, "refresh_token": new_refresh_token}


@account.post("/logout")
def logout(token: str = Depends(oauth2_scheme)):
    try:
        # Пытаемся декодировать токен
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"message": "Logged out successfully"}
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@account.get("/settings")
def get_settings(current_user: User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
    }


@account.post("/forgot-password")
async def forgot_password(request: PasswordResetRequest, session: SessionDep):
    """Request password reset - sends email with reset link"""
    statement = select(User).where(User.email == request.email)
    user = session.exec(statement).first()

    # Don't reveal if email exists or not (security best practice)
    if not user:
        return {"message": "If the email exists, a password reset link has been sent"}

    # Create reset token
    reset_token = create_password_reset_token(user.email)

    # Send email
    try:
        await send_password_reset_email(user.email, reset_token)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to send reset email. Please try again later.",
        )

    return {"message": "If the email exists, a password reset link has been sent"}


@account.post("/reset-password")
def reset_password(reset_data: PasswordResetConfirm, session: SessionDep):
    """Reset password using the token from email"""
    try:
        # Decode and verify token
        payload = jwt.decode(reset_data.token, SECRET_KEY,
                             algorithms=[ALGORITHM])
        email = payload.get("sub")
        token_type = payload.get("type")

        if email is None or token_type != "password_reset":
            raise HTTPException(status_code=401, detail="Invalid reset token")

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Reset token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid reset token")

    # Find user
    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update password
    user.password = hash_password(reset_data.new_password)
    session.add(user)
    session.commit()

    return {"message": "Password has been reset successfully"}
