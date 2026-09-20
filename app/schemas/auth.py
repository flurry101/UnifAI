from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    cpse_id: Optional[str] = None
    auth_provider: Optional[str] = "local"
    avatar_url: Optional[str] = None

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    role: str
    cpse_id: str
    auth_provider: Optional[str] = "local"
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True

class RegisterRequest(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    role: str = "CPSE_USER"
    cpse_id: str = "IOCL"

class GoogleExchangeRequest(BaseModel):
    code: str
    redirect_uri: Optional[str] = None
    state: Optional[str] = None

class SupabaseExchangeRequest(BaseModel):
    supabase_token: str
    role: Optional[str] = "CPSE_USER"
    cpse_id: Optional[str] = "IOCL"

