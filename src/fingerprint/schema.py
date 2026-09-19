from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional

class MaterialFingerprint(BaseModel):
    model_config = ConfigDict(extra='ignore')
    
    # Core identifying representation
    fingerprint_id: str  # The SHA-256 hash
    fingerprint_schema_version: str = "v1"
    
    # State flags
    fingerprint_status: str  # COMPLETE, PARTIAL, AMBIGUOUS, CONFLICTED
    
    # What data went into the hash?
    technical_identity: Dict[str, Any]
    
    # How it was represented before hashing
    canonical_serialization: str
