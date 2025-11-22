import re
from typing import Dict

from pydantic import BaseModel, EmailStr, field_validator

from validation.password_error import _validate_password


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str):
        return _validate_password(password)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_password
