from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.schemas.material import MaterialResponse

router = APIRouter()

from typing import List, Optional

@router.get("", response_model=List[MaterialResponse])
def search_materials(
    search: Optional[str] = None,
    cpse_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    conditions = []
    params = {"limit": limit}
    if search:
        conditions.append("(material_id LIKE :search OR original_material_code LIKE :search OR normalized_description LIKE :search)")
        params["search"] = f"%{search}%"
    if cpse_id:
        conditions.append("cpse_id = :cpse_id")
        params["cpse_id"] = cpse_id
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    query = text(f"""
        SELECT material_id, cpse_id, original_material_code, normalized_description, source_system
        FROM material_retrieval
        {where_clause}
        LIMIT :limit
    """)
    results = db.execute(query, params).fetchall()
    return [
        {
            "material_id": r[0],
            "cpse_id": r[1],
            "original_material_code": r[2],
            "normalized_description": r[3],
            "source_system": r[4]
        }
        for r in results
    ]

@router.get("/{material_id}", response_model=MaterialResponse)
def get_material(material_id: str, db: Session = Depends(get_db)):
    # Support exact ID, original code, or prefix matching
    query = text("""
        SELECT material_id, cpse_id, original_material_code, normalized_description, source_system
        FROM material_retrieval
        WHERE material_id = :material_id 
           OR original_material_code = :material_id
           OR material_id LIKE :prefix
           OR original_material_code LIKE :prefix
        ORDER BY
            CASE
                WHEN material_id = :material_id THEN 0
                WHEN original_material_code = :material_id THEN 1
                ELSE 2
            END,
            material_id ASC,
            original_material_code ASC
        LIMIT 1
    """)
    result = db.execute(query, {"material_id": material_id, "prefix": f"{material_id}%"}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Material not found")
        
    return {
        "material_id": result[0],
        "cpse_id": result[1],
        "original_material_code": result[2],
        "normalized_description": result[3],
        "source_system": result[4]
    }

