from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from config.database import SessionDep
from models.threat import Threat

threats_router = APIRouter(prefix="/api/threats", tags=["Threats"])


@threats_router.get("/", response_model=list[Threat])
def get_threats(session: SessionDep):
    """Отримати всі актуальні загрози"""
    threats = session.exec(select(Threat)).all()
    return threats


@threats_router.post("/", response_model=Threat)
def create_threat(threat: Threat, session: SessionDep):
    """Додати нову загрозу"""
    session.add(threat)
    session.commit()
    session.refresh(threat)
    return threat


@threats_router.delete("/{threat_id}")
def delete_threat(threat_id: str, session: SessionDep):
    """Видалити загрозу"""
    threat = session.get(Threat, threat_id)
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found")
    session.delete(threat)
    session.commit()
    return {"message": "Threat deleted"}
