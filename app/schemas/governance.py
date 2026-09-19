from pydantic import BaseModel
from typing import Optional

class GovernanceDecisionRequest(BaseModel):
    action: str # APPROVE, REJECT, MODIFY
    relationship_override: Optional[str] = None # Optional override if modifying
