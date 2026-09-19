from pydantic import BaseModel
from typing import Optional

class MaterialResponse(BaseModel):
    material_id: str
    cpse_id: str
    original_material_code: Optional[str]
    normalized_description: Optional[str]
    source_system: Optional[str]

    class Config:
        from_attributes = True
