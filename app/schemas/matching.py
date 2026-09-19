from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class MatchRequest(BaseModel):
    query_material_id: str

class MatchProposalResponse(BaseModel):
    id: str
    query_material_id: str
    candidate_material_id: str
    predicted_relation: str
    confidence_level: str
    decision_status: str
    governance_state: str
    lane7_probabilities: Optional[Dict[str, Any]]
    lane8_decision: Optional[Dict[str, Any]]
    model_version: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
