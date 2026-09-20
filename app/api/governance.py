from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.matching import MatchProposalResponse
from app.schemas.governance import GovernanceDecisionRequest
from app.schemas.auth import TokenData
from app.models import MatchProposal
from app.services.governance_service import record_human_decision
from app.security.permissions import get_current_user, require_role

router = APIRouter()

@router.get("/pending", response_model=List[MatchProposalResponse])
def get_review_queue(db: Session = Depends(get_db)):
    # Returns proposals requiring human review (REVIEW status)
    proposals = db.query(MatchProposal).filter(MatchProposal.decision_status == "REVIEW", MatchProposal.governance_state == "PENDING").all()
    return proposals

@router.post("/{proposal_id}/decision", response_model=MatchProposalResponse)
def submit_decision(
    proposal_id: str, 
    request: GovernanceDecisionRequest,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_role(["REVIEWER", "TECHNICAL_REVIEWER", "NATIONAL_ADMIN", "ADMIN", "CPSE_ADMIN"]))
):
    try:
        updated_proposal = record_human_decision(
            db=db,
            proposal_id=proposal_id,
            action=request.action,
            relationship_override=request.relationship_override,
            actor_id=user.username
        )
        return updated_proposal
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/audit-logs")
def get_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_role(["CPSE_ADMIN", "NATIONAL_ADMIN", "ADMIN", "AUDITOR", "TECHNICAL_REVIEWER", "REVIEWER"]))
):
    from app.models import AuditLog
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "entity_name": log.entity_name,
            "entity_id": log.entity_id,
            "actor_id": log.actor_id or "AI_SYSTEM",
            "action": log.action,
            "previous_state": log.previous_state,
            "new_state": log.new_state,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log in logs
    ]


