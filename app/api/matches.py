from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.matching import MatchProposalResponse
from app.services.pipeline_service import match_material
from app.models import MatchProposal

router = APIRouter()

@router.post("/{material_id}/matches", response_model=List[MatchProposalResponse])
def generate_matches(material_id: str, db: Session = Depends(get_db)):
    try:
        proposals = match_material(material_id, db)
        return proposals
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

@router.get("/{material_id}/matches", response_model=List[MatchProposalResponse])
def get_match_proposals(material_id: str, db: Session = Depends(get_db)):
    proposals = db.query(MatchProposal).filter(MatchProposal.query_material_id == material_id).all()
    return proposals

