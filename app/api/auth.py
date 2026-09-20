import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models import User, CpseTenant, ExternalIdentity
from app.security.jwt import verify_password, get_password_hash, create_access_token, SECRET_KEY, ALGORITHM
from app.schemas.auth import Token, RegisterRequest, GoogleExchangeRequest

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/auth/google/callback")
SSO_LOGIN_CALLBACK_URL = os.getenv("SSO_LOGIN_CALLBACK_URL", "http://localhost:5173/auth/google/callback")
OAUTH_STATE_COOKIE = "unifai_oauth_state"
OAUTH_STATE_TTL_SECONDS = 10 * 60

def _is_placeholder_credential(val: str) -> bool:
    if not val:
        return True
    lower = val.lower()
    return "sample" in lower or "placeholder" in lower or "your-" in lower

def _create_oauth_state(redirect_uri: str, client_state: Optional[str]) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "purpose": "google_oauth_state",
            "nonce": secrets.token_urlsafe(32),
            "redirect_uri": redirect_uri,
            "client_state": client_state,
            "iat": now,
            "exp": now + timedelta(seconds=OAUTH_STATE_TTL_SECONDS),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

def _validate_oauth_state(request: Request, state: Optional[str], redirect_uri: str) -> dict:
    cookie_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if not state or not cookie_state or not secrets.compare_digest(state, cookie_state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing or mismatched OAuth state")
    try:
        payload = jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state") from exc
    if (
        payload.get("purpose") != "google_oauth_state"
        or not payload.get("nonce")
        or payload.get("redirect_uri") != redirect_uri
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
    return payload

def _consume_oauth_state(response: Response) -> None:
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/api/v1/auth/google")

def get_current_user(request: Request, token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Synapse-style JWT token validation and current user retrieval dependency.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = token or request.cookies.get("unifai_session")
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

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
        role="CPSE_USER",
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

def _upsert_google_user(db: Session, email: str, name: Optional[str], avatar_url: Optional[str], role: str, cpse_id: str, google_subject: str) -> User:
    email = email.strip().lower()
    identity = db.query(ExternalIdentity).filter(
        ExternalIdentity.provider == "google",
        ExternalIdentity.external_id == google_subject,
    ).first()
    user = identity.user if identity else None

    if not identity and db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Sign in to that account before linking Google.",
        )
    
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
            hashed_password=None,
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
    if not identity:
        db.add(ExternalIdentity(provider="google", external_id=google_subject, user_id=user.id))
    db.commit()
    return user

@router.post("/google/exchange", response_model=Token)
async def google_exchange(
    req: GoogleExchangeRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Standard OAuth 2.0 Authorization Code Exchange (SPA flow):
    Exchanges code for Google tokens, retrieves profile from Google userinfo API,
    and returns authenticated platform JWT session.
    """
    redirect_uri = req.redirect_uri or GOOGLE_REDIRECT_URI
    _validate_oauth_state(request, req.state, redirect_uri)
    _consume_oauth_state(response)

    if _is_placeholder_credential(GOOGLE_CLIENT_ID) or _is_placeholder_credential(GOOGLE_CLIENT_SECRET):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured with active credentials in .env. Please provide valid GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
        )

    async with httpx.AsyncClient(timeout=10.0) as client:
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
        if not google_access_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google OAuth exchange did not return an access token")

        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {google_access_token}"}
        )

        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to retrieve profile from Google UserInfo API")

        profile = userinfo_resp.json()
        email = profile.get("email")
        google_subject = profile.get("sub")
        if not email or profile.get("verified_email") is not True or not google_subject:
            raise HTTPException(status_code=400, detail="Google account did not return a verified email address")

        name = profile.get("name") or profile.get("given_name")
        avatar_url = profile.get("picture")

    user = _upsert_google_user(
        db=db,
        email=email,
        name=name,
        avatar_url=avatar_url,
        role="CPSE_USER",
        cpse_id="IOCL",
        google_subject=google_subject,
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
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Synapse-style server-side Google SSO Callback:
    Processes code, provisions user, and redirects to frontend with ?token=...
    """
    frontend_callback = SSO_LOGIN_CALLBACK_URL
    callback_uri = str(request.url).split("?")[0]
    _validate_oauth_state(request, state, callback_uri)

    def callback_response(**params: str) -> RedirectResponse:
        delimiter = "&" if "?" in frontend_callback else "?"
        response = RedirectResponse(f"{frontend_callback}{delimiter}{urlencode(params)}")
        _consume_oauth_state(response)
        return response

    if error:
        return callback_response(error=error, state=state)
    if not code:
        return callback_response(error="missing_code", state=state)

    if _is_placeholder_credential(GOOGLE_CLIENT_ID) or _is_placeholder_credential(GOOGLE_CLIENT_SECRET):
        return callback_response(error="unconfigured_oauth", state=state)

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": callback_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"}
        )

        if token_resp.status_code != 200:
            return callback_response(error="google_token_exchange_failed", state=state)

        token_json = token_resp.json()
        google_access_token = token_json.get("access_token")
        if not google_access_token:
            return callback_response(error="missing_google_access_token", state=state)

        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {google_access_token}"}
        )

        if userinfo_resp.status_code != 200:
            return callback_response(error="userinfo_failed", state=state)

        profile = userinfo_resp.json()
        email = profile.get("email")
        if not email or profile.get("verified_email") is not True:
            return callback_response(error="missing_email", state=state)
        name = profile.get("name")
        avatar = profile.get("picture")

    google_subject = profile.get("sub")
    if not google_subject:
        return callback_response(error="missing_subject", state=state)
    user = _upsert_google_user(db=db, email=email, name=name, avatar_url=avatar, role="CPSE_USER", cpse_id="IOCL", google_subject=google_subject)
    access_token = create_access_token(data={"sub": user.username, "role": user.role, "email": user.email})

    response = callback_response(session="established", state=state)
    response.set_cookie(
        "unifai_session",
        access_token,
        max_age=3600,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
    )
    return response

@router.get("/google/url")
def get_google_oauth_url(
    request: Request,
    response: Response,
    redirect_uri: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
):
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
    
    signed_state = _create_oauth_state(target_redirect, state)
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": target_redirect,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
        "state": signed_state,
    }
    oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        signed_state,
        max_age=OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        path="/api/v1/auth/google",
    )
    return {
        "oauth_url": oauth_url,
        "state": signed_state,
        "configured": True,
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": target_redirect
    }
