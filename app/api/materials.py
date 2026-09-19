from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.schemas.material import MaterialResponse

router = APIRouter()

@router.get("/{material_id}", response_model=MaterialResponse)
def get_material(material_id: str, db: Session = Depends(get_db)):
    # Reading directly from existing Lane 5 material_retrieval table using text()
    # because we explicitly did NOT model it in SQLAlchemy to prevent migration conflicts.
    query = text("""
        SELECT material_id, cpse_id, original_material_code, normalized_description, source_system
        FROM material_retrieval
        WHERE material_id = :material_id
    """)
    result = db.execute(query, {"material_id": material_id}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Material not found")
        
    return {
        "material_id": result[0],
        "cpse_id": result[1],
        "original_material_code": result[2],
        "normalized_description": result[3],
        "source_system": result[4]
    }

