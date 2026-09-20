"""
Admin endpoints for user management.

Access control:
  - NATIONAL_ADMIN : full access (list all users, set any role)
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.api.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_ROLES = {"CPSE_USER", "TECHNICAL_REVIEWER", "NATIONAL_ADMIN", "AUDITOR"}
ADMIN_ONLY_ROLES = {"NATIONAL_ADMIN"}

# ── Helpers ─────────────────────────────────────────────────────────────────────

def _require_admin(current_user: User) -> User:
    if current_user.role != "NATIONAL_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


# ── Schemas ──────────────────────────────────────────────────────────────────────

class UserSummary(BaseModel):
    id: str
    username: str
    email: Optional[str]
    role: str
    cpse_id: Optional[str]
    auth_provider: Optional[str]
    avatar_url: Optional[str]

    class Config:
        from_attributes = True


class RoleUpdateRequest(BaseModel):
    role: str


# ── Endpoints ────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=List[UserSummary])
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all registered users.
    NATIONAL_ADMIN sees everyone.
    """
    _require_admin(current_user)
    query = db.query(User)
    return query.order_by(User.id).all()


@router.patch("/users/{user_id}/role", response_model=UserSummary)
async def update_user_role(
    user_id: str,
    req: RoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change a user's role.
    - NATIONAL_ADMIN can assign any role to any user.
    """
    _require_admin(current_user)

    new_role = req.role.upper().strip()
    if new_role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{new_role}'. Valid roles: {sorted(VALID_ROLES)}",
        )

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # Prevent removing the last NATIONAL_ADMIN
    if target.role == "NATIONAL_ADMIN" and new_role != "NATIONAL_ADMIN":
        remaining_admins = db.query(User).filter(
            User.role == "NATIONAL_ADMIN", User.id != user_id
        ).count()
        if remaining_admins == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot remove the last NATIONAL_ADMIN. Promote another user first.",
            )

    logger.info(
        "Role change: user=%s changed %s (%s) → %s",
        current_user.username, target.username, target.role, new_role,
    )
    target.role = new_role
    db.commit()
    db.refresh(target)

    # Sync role to Supabase Auth if the user has an email
    if target.email:
        try:
            from app.core.supabase_admin import sync_role_to_supabase_user
            await sync_role_to_supabase_user(target.email, new_role)
        except Exception as e:
            logger.warning("Could not sync role to Supabase Auth: %s", e)

    return target

