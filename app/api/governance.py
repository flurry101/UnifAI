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
    user: TokenData = Depends(require_role(["REVIEWER", "TECHNICAL_REVIEWER", "NATIONAL_ADMIN", "ADMIN"]))
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

