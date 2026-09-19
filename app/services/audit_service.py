from sqlalchemy.orm import Session
from app.models import AuditLog
import json
from typing import Optional, Dict, Any

def log_audit_event(
    db: Session,
    entity_name: str,
    entity_id: str,
    action: str,
    actor_id: Optional[str] = None,
    previous_state: Optional[Dict[str, Any]] = None,
    new_state: Optional[Dict[str, Any]] = None
):
    audit_entry = AuditLog(
        entity_name=entity_name,
        entity_id=entity_id,
        action=action,
        actor_id=actor_id,
        previous_state=previous_state,
        new_state=new_state
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry
