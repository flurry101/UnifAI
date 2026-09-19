from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.cnmc import CnmcResponse
from app.models import CnmcRegistry

router = APIRouter()

@router.get("/", response_model=List[CnmcResponse])
@router.get("/catalog", response_model=List[CnmcResponse])
def list_cnmc(db: Session = Depends(get_db)):
    return db.query(CnmcRegistry).all()

@router.get("/{cnmc_id}", response_model=CnmcResponse)
def get_cnmc_details(cnmc_id: str, db: Session = Depends(get_db)):
    cnmc = db.query(CnmcRegistry).filter((CnmcRegistry.id == cnmc_id) | (CnmcRegistry.cnmc_code == cnmc_id)).first()
    if not cnmc:
        raise HTTPException(status_code=404, detail="CNMC not found")
    return cnmc
