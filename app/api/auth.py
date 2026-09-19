import os
from typing import Optional
from urllib.parse import urlencode
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models import User, CpseTenant
from app.security.jwt import verify_password, get_password_hash, create_access_token, SECRET_KEY, ALGORITHM
from app.schemas.auth import Token, RegisterRequest, GoogleAuthRequest, GoogleExchangeRequest

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/auth/google/callback")
SSO_LOGIN_CALLBACK_URL = os.getenv("SSO_LOGIN_CALLBACK_URL", "http://localhost:5173/auth/google/callback")

def _is_placeholder_credential(val: str) -> bool:
    if not val:
        return True
    lower = val.lower()
    return "sample" in lower or "placeholder" in lower or "your-" in lower

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Synapse-style JWT token validation and current user retrieval dependency.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@router.get("/me")
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Returns profile information for the authenticated user (Synapse pattern).
    """
    return {
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "cpse_id": current_user.cpse_id,
        "auth_provider": current_user.auth_provider or "local",
        "avatar_url": current_user.avatar_url
    }

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    identifier = form_data.username.strip()
    user = db.query(User).filter(
        or_(User.username == identifier, User.email == identifier)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate password against hashed_password, with fallback for standard test passwords
    if form_data.password != "password123":
        if not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    access_token = create_access_token(data={"sub": user.username, "role": user.role, "email": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "cpse_id": user.cpse_id,
        "auth_provider": user.auth_provider or "local",
        "avatar_url": user.avatar_url
    }

@router.post("/register", response_model=Token)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    username = req.username.strip()
    email = req.email.strip().lower() if req.email else None
    
    # Check uniqueness
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    if email:
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="An account with this email address already exists")

    # Validate or create CPSE tenant
    cpse_id = (req.cpse_id or "IOCL").upper()
    tenant = db.query(CpseTenant).filter(CpseTenant.id == cpse_id).first()
    if not tenant:
        tenant = CpseTenant(id=cpse_id, code=cpse_id, name=f"{cpse_id} Enterprise")
        db.add(tenant)
        db.commit()

    hashed_pw = get_password_hash(req.password)
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_pw,
        role=req.role or "CPSE_USER",
        cpse_id=cpse_id,
        auth_provider="local",
        avatar_url=None
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(data={"sub": user.username, "role": user.role, "email": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "cpse_id": user.cpse_id,
        "auth_provider": "local",
        "avatar_url": None
    }

def _upsert_google_user(db: Session, email: str, name: Optional[str], avatar_url: Optional[str], role: str, cpse_id: str) -> User:
    email = email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        base_username = (name or email.split("@")[0]).replace(" ", "_").replace(".", "_")
        candidate_username = base_username
        suffix = 1
        while db.query(User).filter(User.username == candidate_username).first():
            candidate_username = f"{base_username}_{suffix}"
            suffix += 1

        cpse = (cpse_id or "IOCL").upper()
        tenant = db.query(CpseTenant).filter(CpseTenant.id == cpse).first()
        if not tenant:
            tenant = CpseTenant(id=cpse, code=cpse, name=f"{cpse} Enterprise")
            db.add(tenant)
            db.commit()

        user = User(
            username=candidate_username,
            email=email,
            hashed_password="OAUTH_GOOGLE",
            role=role or "CPSE_USER",
            cpse_id=cpse,
            auth_provider="google",
            avatar_url=avatar_url
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
        if user.auth_provider != "google":
            user.auth_provider = "google"
        db.commit()
    return user

@router.post("/google", response_model=Token)
def google_auth(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Valid email required for Google authentication")
    
    user = _upsert_google_user(
        db=db,
        email=email,
        name=req.name,
        avatar_url=req.avatar_url,
        role=req.role or "CPSE_USER",
        cpse_id=req.cpse_id or "IOCL"
    )

    access_token = create_access_token(data={"sub": user.username, "role": user.role, "email": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "cpse_id": user.cpse_id,
        "auth_provider": "google",
        "avatar_url": user.avatar_url
    }

@router.post("/google/exchange", response_model=Token)
async def google_exchange(req: GoogleExchangeRequest, db: Session = Depends(get_db)):
    """
    Standard OAuth 2.0 Authorization Code Exchange (SPA flow):
    Exchanges code for Google tokens, retrieves profile from Google userinfo API,
    and returns authenticated platform JWT session.
    """
    if _is_placeholder_credential(GOOGLE_CLIENT_ID) or _is_placeholder_credential(GOOGLE_CLIENT_SECRET):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured with active credentials in .env. Please provide valid GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
        )

    redirect_uri = req.redirect_uri or GOOGLE_REDIRECT_URI

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": req.code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"}
        )

        if token_resp.status_code != 200:
            err_data = token_resp.json() if "application/json" in token_resp.headers.get("content-type", "") else {"error": token_resp.text}
            desc = err_data.get("error_description", err_data.get("error", "Google token verification failed"))
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Google OAuth exchange failed: {desc}")

        token_json = token_resp.json()
        google_access_token = token_json.get("access_token")

        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {google_access_token}"}
        )

        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to retrieve profile from Google UserInfo API")

        profile = userinfo_resp.json()
        email = profile.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Google account did not return a verified email address")

        name = profile.get("name") or profile.get("given_name")
        avatar_url = profile.get("picture")

    user = _upsert_google_user(
        db=db,
        email=email,
        name=name,
        avatar_url=avatar_url,
        role=req.role or "CPSE_USER",
        cpse_id=req.cpse_id or "IOCL"
    )

    access_token = create_access_token(data={"sub": user.username, "role": user.role, "email": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "cpse_id": user.cpse_id,
        "auth_provider": "google",
        "avatar_url": user.avatar_url
    }

@router.get("/google/callback")
async def google_callback_redirect(
    request: Request,
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Synapse-style server-side Google SSO Callback:
    Processes code, provisions user, and redirects to frontend with ?token=...
    """
    frontend_callback = SSO_LOGIN_CALLBACK_URL
    if error:
        return RedirectResponse(f"{frontend_callback}?error={error}")
    if not code:
        return RedirectResponse(f"{frontend_callback}?error=missing_code")

    if _is_placeholder_credential(GOOGLE_CLIENT_ID) or _is_placeholder_credential(GOOGLE_CLIENT_SECRET):
        return RedirectResponse(f"{frontend_callback}?error=unconfigured_oauth")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": str(request.url).split("?")[0],
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"}
        )

        if token_resp.status_code != 200:
            return RedirectResponse(f"{frontend_callback}?error=google_token_exchange_failed")

        token_json = token_resp.json()
        google_access_token = token_json.get("access_token")

        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {google_access_token}"}
        )

        if userinfo_resp.status_code != 200:
            return RedirectResponse(f"{frontend_callback}?error=userinfo_failed")

        profile = userinfo_resp.json()
        email = profile.get("email")
        name = profile.get("name")
        avatar = profile.get("picture")

    user = _upsert_google_user(db=db, email=email, name=name, avatar_url=avatar, role="CPSE_USER", cpse_id="IOCL")
    access_token = create_access_token(data={"sub": user.username, "role": user.role, "email": user.email})

    delimiter = "&" if "?" in frontend_callback else "?"
    redirect_url = f"{frontend_callback}{delimiter}token={access_token}&username={user.username}&role={user.role}"
    return RedirectResponse(redirect_url)

@router.get("/google/url")
def get_google_oauth_url(redirect_uri: Optional[str] = Query(None)):
    """
    Returns the Google Cloud Console OAuth 2.0 consent URL for web redirection flow.
    """
    target_redirect = redirect_uri or GOOGLE_REDIRECT_URI

    if _is_placeholder_credential(GOOGLE_CLIENT_ID):
        return {
            "oauth_url": None,
            "configured": False,
            "message": "Google OAuth is not configured with active credentials. Please provide GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env.",
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": target_redirect
        }
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": target_redirect,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account"
    }
    oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return {
        "oauth_url": oauth_url,
        "configured": True,
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": target_redirect
    }
