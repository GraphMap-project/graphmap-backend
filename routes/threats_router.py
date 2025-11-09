from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from config.database import SessionDep
from models.threat import Threat
from models.user import User
from routes.account import get_current_user
from validation.role_validation import can_manage_threats

threats_router = APIRouter(prefix="/api/threats", tags=["Threats"])


@threats_router.get("/", response_model=list[Threat])
def get_threats(session: SessionDep):
    threats = session.exec(select(Threat)).all()
    return threats


@threats_router.post("/", response_model=Threat)
def create_threat(threat: Threat,
                  session: SessionDep,
                  current_user: User = Depends(get_current_user)):

    if not can_manage_threats(current_user.role):
        raise HTTPException(
            status_code=403, detail="You are not allowed to create threats")

    data = threat.model_dump(exclude={"created_by"})
    new_threat = Threat(**data, created_by=current_user.id)
    session.add(new_threat)
    session.commit()
    session.refresh(new_threat)
    return new_threat


@threats_router.delete("/{threat_id}")
def delete_threat(threat_id: str,
                  session: SessionDep,
                  current_user: User = Depends(get_current_user)):

    if not can_manage_threats(current_user.role):
        raise HTTPException(
            status_code=403, detail="You are not allowed to delete threats")

    threat = session.get(Threat, threat_id)

    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found")

    session.delete(threat)
    session.commit()

    return {"message": "Threat deleted"}
