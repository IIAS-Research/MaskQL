# app/core.py
import os
from typing import Optional
import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from maskql.security.password import hash_password

TRINO_URL = os.getenv("TRINO_URL", "http://trino:8080").rstrip("/")
CONNECT_TIMEOUT = float(os.getenv("CONNECT_TIMEOUT", "10"))
READ_TIMEOUT = float(os.getenv("READ_TIMEOUT", "3600"))
MAX_CONN = int(os.getenv("MAX_CONN", "200"))
MAX_KEEPALIVE = int(os.getenv("MAX_KEEPALIVE", "50"))

ADMIN_USER = os.getenv("MASKQL_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("MASKQL_ADMIN_PASSWORD_HASH", "$2y$12$w2WWdzvBAUFWaz9zPsRVBOFBtCB9zVBOnSSHc34HD3yFQES4BePLC") # default : admin
DEMO_USER = [("admin", "admin"), ("test", "test")]


async def require_gateway_auth(creds: HTTPBasicCredentials = Depends(HTTPBasic())) -> str:
    for user, password in DEMO_USER:
        if creds.username == user and creds.password == password:
            return creds.username
    raise HTTPException(status_code=401, detail="Unauthorized")

async def require_admin_auth(creds: HTTPBasicCredentials = Depends(HTTPBasic())) -> str:
    if creds.username == ADMIN_USER and hash_password(creds.password) == ADMIN_PASSWORD:
            return ADMIN_USER
    raise HTTPException(status_code=401, detail="Unauthorized")

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