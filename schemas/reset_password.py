import re

from pydantic import BaseModel, EmailStr, field_validator

from validation.password_error import _validate_password


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, password: str):
        return _validate_password(password)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_password
