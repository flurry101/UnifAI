from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import CnmcRegistry, CpseCnmcMapping, MatchProposal
import uuid

def generate_cnmc_code(db: Session) -> str:
    # A simple deterministic sequence or UUID based CNMC generator for the prototype
    count = db.query(CnmcRegistry).count()
    return f"CNMC-{10000 + count + 1}"

def create_cnmc_from_proposal(db: Session, proposal: MatchProposal) -> CnmcRegistry:
    # Look up original materials to build standardized description
    query_text = text("SELECT normalized_description FROM material_retrieval WHERE material_id = :id")
    q_row = db.execute(query_text, {"id": proposal.query_material_id}).fetchone()
    
    # We take the query's normalized description as the standard for now.
    std_desc = q_row[0] if q_row else "Standardized Description"
    
    cnmc = CnmcRegistry(
        cnmc_code=generate_cnmc_code(db),
        standardized_description=std_desc,
        status="APPROVED"
    )
    db.add(cnmc)
    db.flush() # flush to get cnmc.id
    return cnmc
