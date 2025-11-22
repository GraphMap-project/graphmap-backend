from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from config.database import SessionDep
from config.roles import Role
from models.threat import Threat
from models.threat_request import RequestAction, RequestStatus, ThreatRequest
from models.user import User
from routes.account import get_current_user
from schemas.threat_request_create import ThreatRequestCreate
from validation.role_validation import can_manage_threats

threats_router = APIRouter(prefix="/api/threats", tags=["Threats"])


@threats_router.get("/", response_model=list[Threat])
def get_threats(session: SessionDep):
    threats = session.exec(select(Threat)).all()
    return threats


@threats_router.post("/")
def create_threat(
    threat_data: ThreatRequestCreate,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Create threat - direct for threat-responsible, request for military"""

    # Threat-responsible users can create directly
    if can_manage_threats(current_user.role):
        new_threat = Threat(
            type=threat_data.type,
            description=threat_data.description,
            location=[loc.model_dump() for loc in threat_data.location],
            created_by=current_user.id,
        )
        session.add(new_threat)
        session.commit()
        session.refresh(new_threat)
        return {"message": "Threat created"}

    # Military users create a creation request
    if current_user.role == Role.MILITARY.value:
        request = ThreatRequest(
            action=RequestAction.CREATE,
            threat_type=threat_data.type,
            description=threat_data.description,
            location=[loc.model_dump() for loc in threat_data.location],
            requested_by=current_user.id,
        )
        session.add(request)
        session.commit()
        session.refresh(request)
        return {"message": "Creation request created", "request_id": str(request.id)}


@threats_router.delete("/{threat_id}")
def delete_threat(
    threat_id: str,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Delete threat - direct for threat-responsible, request for military"""
    threat = session.get(Threat, threat_id)
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found")

    # Threat-responsible users can delete directly
    if can_manage_threats(current_user.role):
        session.delete(threat)
        session.commit()
        return {"message": "Threat deleted"}

    # Military users create a deletion request
    if current_user.role == Role.MILITARY.value:
        request = ThreatRequest(
            action=RequestAction.DELETE,
            threat_id=threat.id,
            requested_by=current_user.id,
        )
        session.add(request)
        session.commit()
        session.refresh(request)
        return {"message": "Deletion request created", "request_id": str(request.id)}


@threats_router.get("/requests", response_model=list[ThreatRequest])
def get_threat_requests(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get all pending threat requests"""
    if not can_manage_threats(current_user.role):
        raise HTTPException(
            status_code=403, detail="Only threat-responsible users can view requests"
        )

    query = select(ThreatRequest).where(
        ThreatRequest.status == RequestStatus.PENDING)

    requests = session.exec(query.order_by(
        ThreatRequest.created_at.desc())).all()
    return requests


@threats_router.post("/requests/{request_id}/approve")
def approve_request(
    request_id: str,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Approve a threat request"""
    if not can_manage_threats(current_user.role):
        raise HTTPException(
            status_code=403,
            detail="Only threat-responsible users can approve requests",
        )

    request = session.get(ThreatRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=400, detail="Request already processed")

    request.status = RequestStatus.APPROVED
    request.reviewed_by = current_user.id
    request.reviewed_at = datetime.utcnow()

    if request.action == RequestAction.CREATE:
        threat = Threat(
            type=request.threat_type,
            description=request.description,
            location=request.location,
            created_by=str(request.requested_by),
        )
        session.add(threat)
        session.commit()
        session.refresh(threat)
        return {"message": "Threat created"}
    else:  # DELETE
        threat = session.get(Threat, request.threat_id)
        if threat:
            session.delete(threat)
        session.commit()
        return {"message": "Threat deleted"}


@threats_router.post("/requests/{request_id}/decline")
def decline_request(
    request_id: str,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Decline a threat request"""
    if not can_manage_threats(current_user.role):
        raise HTTPException(
            status_code=403, detail="Only threat-responsible users can decline requests"
        )

    request = session.get(ThreatRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=400, detail="Request already processed")

    request.status = RequestStatus.DECLINED
    request.reviewed_by = current_user.id
    request.reviewed_at = datetime.utcnow()

    session.commit()

    return {"message": "Request declined"}
