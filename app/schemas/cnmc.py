from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class CnmcResponse(BaseModel):
    id: str
    cnmc_code: str
    standardized_description: str
    core_attributes: Optional[Dict[str, Any]]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
