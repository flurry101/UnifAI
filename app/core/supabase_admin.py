"""
Supabase Admin API helpers for server-side management.
Uses SUPABASE_SERVICE_ROLE_KEY to administer users in Supabase Auth.
"""

import os
import logging
import httpx
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


async def get_supabase_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Look up a user in Supabase Auth by email."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/auth/v1/admin/users",
                headers={
                    "apikey": SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                for user in data.get("users", []):
                    if user.get("email", "").lower() == email.lower():
                        return user
    except Exception as e:
        logger.warning("Error fetching Supabase user by email %s: %s", email, e)
    return None


async def sync_role_to_supabase_user(email_or_uid: str, role: str) -> bool:
    """
    Updates app_metadata on the Supabase Auth user record so their
    Supabase JWT includes the role claim.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase URL or Service Role Key missing. Cannot sync role.")
        return False

    user_id = email_or_uid
    if "@" in email_or_uid:
        user = await get_supabase_user_by_email(email_or_uid)
        if not user:
            logger.warning("Could not find Supabase user with email %s", email_or_uid)
            return False
        user_id = user["id"]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(
                f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
                headers={
                    "apikey": SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "app_metadata": {
                        "role": role,
                        "unifai_role": role,
                    }
                },
            )
            if resp.status_code == 200:
                logger.info("Successfully synced role %s to Supabase user %s", role, user_id)
                return True
            else:
                logger.error("Failed to sync role to Supabase: %s %s", resp.status_code, resp.text)
                return False
    except Exception as e:
        logger.error("Exception syncing role to Supabase user %s: %s", user_id, e)
        return False
