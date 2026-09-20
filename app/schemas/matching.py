from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class MatchRequest(BaseModel):
    query_material_id: str

class MatchProposalResponse(BaseModel):
    id: str
    query_material_id: str
    source_material_id: Optional[str] = None
    source_cpse: Optional[str] = None
    source_description: Optional[str] = None
    candidate_material_id: str
    candidate_cpse: Optional[str] = None
    candidate_description: Optional[str] = None
    predicted_relation: str
    confidence_level: str
    decision_status: str
    governance_state: str
    lane7_probabilities: Optional[Dict[str, Any]] = None
    lane8_decision: Optional[Dict[str, Any]] = None
    comparisons: Optional[List[Dict[str, Any]]] = None
    model_version: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
