import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
from app.database import get_db
from app.schemas.matching import MatchProposalResponse
from app.schemas.governance import GovernanceDecisionRequest
from app.schemas.auth import TokenData
from app.models import MatchProposal
from app.services.governance_service import record_human_decision
from app.security.permissions import get_current_user, require_role

router = APIRouter()

def _extract_attrs(desc: str) -> Dict[str, str]:
    if not desc:
        return {}
    t = desc.upper()
    attrs = {}
    for cat in ["VALVE", "PIPE", "CYLINDER", "TUBE", "FLANGE", "GASKET", "FITTING", "PUMP"]:
        if cat in t:
            attrs["COMMODITY TYPE"] = cat
            break
    m = re.search(r'\b(\d+(?:\.\d+)?\s*(?:INCH|IN|MM|KG|LITERS|DN\s*\d+))\b', t)
    if m:
        attrs["SIZE / DIMENSION"] = m.group(1)
    m = re.search(r'\b(\d+#|CL\s*\d+|CLASS\s*\d+|PN\s*\d+|\d+\s*BAR|SCH\s*\d+)\b', t)
    if m:
        attrs["PRESSURE / CLASS"] = m.group(1)
    m = re.search(r'\b(WCB|SS\s*316L?|316L?|CARBON STEEL|ALLOY STEEL|T22|X65|CS)\b', t)
    if m:
        attrs["MATERIAL GRADE"] = m.group(1)
    m = re.search(r'\b(IS:?\s*\d+(?:\s*PART\s*\d+)?|API\s*[0-9A-Z]+|ASME\s*[0-9A-Z]+|ASTM\s*[0-9A-Z]+)\b', t)
    if m:
        attrs["STANDARD / SPEC"] = m.group(1)
    return attrs

def _build_comparisons(desc_a: str, desc_b: str) -> List[Dict[str, Any]]:
    attrs_a = _extract_attrs(desc_a)
    attrs_b = _extract_attrs(desc_b)
    keys = list(dict.fromkeys(list(attrs_a.keys()) + list(attrs_b.keys())))
    if not keys:
        keys = ["COMMODITY TYPE", "SIZE / DIMENSION", "MATERIAL GRADE"]
    comparisons = []
    for k in keys:
        val_a = attrs_a.get(k, "SPECIFIED IN QUERY")
        val_b = attrs_b.get(k, "SPECIFIED IN CANDIDATE")
        is_match = (val_a.strip().upper() == val_b.strip().upper()) if val_a and val_b else False
        is_conflict = not is_match
        comparisons.append({
            "attribute": k,
            "valA": val_a,
            "valB": val_b,
            "match": is_match,
            "conflict": is_conflict
        })
    return comparisons

@router.get("/pending", response_model=List[MatchProposalResponse])
def get_review_queue(db: Session = Depends(get_db)):
    # Returns proposals requiring human review (REVIEW status)
    proposals = db.query(MatchProposal).filter(MatchProposal.decision_status == "REVIEW", MatchProposal.governance_state == "PENDING").all()
    results = []
    for p in proposals:
        resp = MatchProposalResponse.from_orm(p) if hasattr(MatchProposalResponse, "from_orm") else MatchProposalResponse.model_validate(p)
        resp.source_material_id = p.query_material_id
        
        q_row = db.execute(text("SELECT cpse_id, normalized_description FROM material_retrieval WHERE material_id = :id OR original_material_code = :id LIMIT 1"), {"id": p.query_material_id}).fetchone()
        c_row = db.execute(text("SELECT cpse_id, normalized_description FROM material_retrieval WHERE material_id = :id OR original_material_code = :id LIMIT 1"), {"id": p.candidate_material_id}).fetchone()
        
        resp.source_cpse = q_row[0] if q_row else ("IOCL" if "IOCL" in p.query_material_id else "ONGC")
        resp.source_description = q_row[1] if q_row else f"Material Master Record {p.query_material_id}"
        resp.candidate_cpse = c_row[0] if c_row else ("GAIL" if "GAIL" in p.candidate_material_id else ("NTPC" if "NTPC" in p.candidate_material_id else "EXTERNAL"))
        resp.candidate_description = c_row[1] if c_row else f"Candidate Material Specification {p.candidate_material_id}"
        resp.comparisons = _build_comparisons(resp.source_description, resp.candidate_description)
        results.append(resp)
    return results

@router.post("/{proposal_id}/decision", response_model=MatchProposalResponse)
def submit_decision(
    proposal_id: str, 
    request: GovernanceDecisionRequest,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_role(["CPSE_USER", "REVIEWER", "TECHNICAL_REVIEWER", "NATIONAL_ADMIN", "ADMIN"]))
):
    try:
        updated_proposal = record_human_decision(
            db=db,
            proposal_id=proposal_id,
            action=request.action,
            relationship_override=request.relationship_override,
            actor_id=user.username
        )
        resp = MatchProposalResponse.from_orm(updated_proposal) if hasattr(MatchProposalResponse, "from_orm") else MatchProposalResponse.model_validate(updated_proposal)
        return resp
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/audit-logs")
def get_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_role(["CPSE_USER", "NATIONAL_ADMIN", "ADMIN", "AUDITOR", "TECHNICAL_REVIEWER", "REVIEWER"]))
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
