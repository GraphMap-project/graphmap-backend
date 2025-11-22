from fastapi import HTTPException

from config.roles import Role


def can_manage_threats(role: str):
    if role != Role.THREAT_RESPONSIBLE.value:
        return False

    return True
