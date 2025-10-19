import re
from typing import Dict


class PasswordError(ValueError):
    def __init__(self, errors: Dict[str, str]):
        self.errors = errors
        super().__init__("Password validation failed")


def _validate_password(password: str) -> str:
    """
    Reusable password validator. Raises PasswordError on validation failures,
    otherwise returns the original password.
    """
    errors: Dict[str, str] = {}

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
