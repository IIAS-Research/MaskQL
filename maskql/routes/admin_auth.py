import os
from fastapi import APIRouter, Depends, Response, HTTPException
from pydantic import BaseModel
from maskql.core import (
    security_basic, _verify_admin_password, _create_admin_token,
    ADMIN_USER, ADMIN_JWT_EXPIRE_MIN, require_admin_token
)

router = APIRouter(prefix="/admin", tags=["admin-auth"])

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

@router.post("/login", response_model=TokenResponse)
async def admin_login(creds = Depends(security_basic)):
    if creds.username != ADMIN_USER or not _verify_admin_password(creds.password, os.getenv("MASKQL_ADMIN_PASSWORD","")):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = _create_admin_token(ADMIN_USER)

    resp = Response(
        content=TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=ADMIN_JWT_EXPIRE_MIN * 60,
        ).model_dump_json(),
        media_type="application/json",
    )

    resp.set_cookie(
        key="admin_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ADMIN_JWT_EXPIRE_MIN * 60,
        path="/",
    )
    
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Pragma"] = "no-cache"
    return resp

@router.post("/logout", status_code=204)
async def admin_logout():
    resp = Response(status_code=204)
    resp.delete_cookie("admin_token", path="/")
    return resp

@router.get("/health", status_code=204)
@router.head("/health", status_code=204)
async def admin_ping(_: str = Depends(require_admin_token)):
    return Response(
        status_code=204,
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )