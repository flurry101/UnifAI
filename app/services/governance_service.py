from sqlalchemy.orm import Session
from app.models import MatchProposal, CpseCnmcMapping
from app.services.audit_service import log_audit_event
from app.services.cnmc_service import create_cnmc_from_proposal
from typing import Optional

def record_human_decision(
    db: Session, 
    proposal_id: str, 
    action: str, 
    relationship_override: Optional[str] = None,
    actor_id: Optional[str] = None
):
    """
    Records a human decision on a MatchProposal.
    action: APPROVE, REJECT, MODIFY
    """
    proposal = db.query(MatchProposal).filter(MatchProposal.id == proposal_id).first()
    if not proposal:
        raise ValueError(f"Proposal {proposal_id} not found")
        
    old_state = {
        "governance_state": proposal.governance_state,
        "predicted_relation": proposal.predicted_relation
    }
    
    if action == "APPROVE":
        proposal.governance_state = "APPROVED"
        # Only create CNMC mappings for IDENTICAL/EQUIVALENT
        if proposal.predicted_relation in ["IDENTICAL", "EQUIVALENT"]:
            _create_mapping(db, proposal)
            
    elif action == "REJECT":
        proposal.governance_state = "REJECTED"
        
    elif action == "MODIFY":
        proposal.governance_state = "MODIFIED"
        if relationship_override:
            proposal.predicted_relation = relationship_override
            if relationship_override in ["IDENTICAL", "EQUIVALENT"]:
                _create_mapping(db, proposal)
    else:
        raise ValueError(f"Invalid action {action}")
        
    new_state = {
        "governance_state": proposal.governance_state,
        "predicted_relation": proposal.predicted_relation
    }
    
    db.commit()
    
    log_audit_event(
        db=db,
        entity_name="MATCH_PROPOSAL",
        entity_id=proposal.id,
        action=f"GOVERNANCE_{action}",
        actor_id=actor_id,
        previous_state=old_state,
        new_state=new_state
    )
    
    return proposal

def _create_mapping(db: Session, proposal: MatchProposal):
    # Check if a mapping already exists to prevent duplicates
    existing = db.query(CpseCnmcMapping).filter(CpseCnmcMapping.match_proposal_id == proposal.id).first()
    if existing:
        return existing
        
    # Generate new CNMC
    cnmc = create_cnmc_from_proposal(db, proposal)
    
    # Map BOTH materials to this CNMC
    mapping1 = CpseCnmcMapping(
        cpse_material_id=proposal.query_material_id,
        cnmc_id=cnmc.id,
        relationship_type=proposal.predicted_relation,
        match_proposal_id=proposal.id
    )
    
    mapping2 = CpseCnmcMapping(
        cpse_material_id=proposal.candidate_material_id,
        cnmc_id=cnmc.id,
        relationship_type=proposal.predicted_relation,
        match_proposal_id=proposal.id
    )
    
    db.add(mapping1)
    db.add(mapping2)
    db.flush()
    return [mapping1, mapping2]

