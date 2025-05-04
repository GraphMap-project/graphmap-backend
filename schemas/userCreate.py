import re
from typing import Dict

from pydantic import BaseModel, EmailStr, ValidationError, field_validator


class PasswordError(ValueError):
    def __init__(self, errors: Dict[str, str]):
        self.errors = errors
        super().__init__("Password validation failed")


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str):
        errors = {}

        if not (8 <= len(password) <= 50):
            errors["length"] = "Password must be between 8 and 50 characters long"

        if not re.search(r"[a-z]", password):
            errors["lowercase"] = "Password must contain at least one lowercase letter"

        if not re.search(r"[A-Z]", password):
            errors["uppercase"] = "Password must contain at least one uppercase letter"

        if not re.search(r"\d", password):
            errors["digit"] = "Password must contain at least one digit"

        if not re.search(r"[@$!%*?&]", password):
            errors["special"] = (
                "Password must contain at least one special character (@$!%*?&)"
            )

        if errors:
            raise PasswordError(errors)

        return password

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_password
