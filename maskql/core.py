# app/core.py
import os, secrets
from typing import Optional
import httpx
from fastapi import Depends, HTTPException, Header, Cookie
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt, JWTError

from maskql.services.user_service import UserService

TRINO_URL = os.getenv("TRINO_URL", "http://trino:8080").rstrip("/")
CONNECT_TIMEOUT = float(os.getenv("CONNECT_TIMEOUT", "10"))
READ_TIMEOUT = float(os.getenv("READ_TIMEOUT", "3600"))
MAX_CONN = int(os.getenv("MAX_CONN", "200"))
MAX_KEEPALIVE = int(os.getenv("MAX_KEEPALIVE", "50"))


security_basic = HTTPBasic(realm="Admin area")
pwd_context = CryptContext(schemes=["bcrypt", "argon2"], deprecated="auto")
ADMIN_USER = os.getenv("MASKQL_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("MASKQL_ADMIN_PASSWORD_HASH","admin")
JWT_SECRET = os.getenv("MASKQL_JWT_SECRET", secrets.token_urlsafe(32))
JWT_ALG = "HS256"
ADMIN_JWT_EXPIRE_MIN = int(os.getenv("MASKQL_ADMIN_JWT_EXPIRE_MIN", "30"))


async def require_gateway_auth(creds: HTTPBasicCredentials = Depends(HTTPBasic())) -> str:
    if user := await UserService.authenticate(creds.username, creds.password):
        return user.username
    raise HTTPException(status_code=401, detail="Unauthorized")

def _verify_admin_password(plain: str, stored: str) -> bool:
    if stored.startswith(("$2a$", "$2b$", "$2y$", "$argon2")):
        try:
            return pwd_context.verify(plain, stored)
        except Exception:
            return False
    return secrets.compare_digest(plain, stored)

def _create_admin_token(subject: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=ADMIN_JWT_EXPIRE_MIN)
    payload = {"sub": subject, "role": "admin", "exp": exp}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def _decode_admin_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("sub") != ADMIN_USER or payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return payload["sub"]

async def _get_token_from_req(
    authorization: Optional[str] = Header(default=None),
    admin_token_cookie: Optional[str] = Cookie(default=None, alias="admin_token"),
) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1]
    if admin_token_cookie:
        return admin_token_cookie
    raise HTTPException(status_code=401, detail="Missing token")

async def require_admin_token(token: str = Depends(_get_token_from_req)) -> str:
    return _decode_admin_token(token)

_client: Optional[httpx.AsyncClient] = None
async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(CONNECT_TIMEOUT, read=READ_TIMEOUT),
            limits=httpx.Limits(max_connections=MAX_CONN, max_keepalive_connections=MAX_KEEPALIVE),
            http2=False,
        )
    return _client

async def close_client():
    global _client
    if _client:
        await _client.aclose()
        _client = None