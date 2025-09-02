from fastapi import APIRouter, Depends, Request
import httpx
from fastapi.responses import JSONResponse, StreamingResponse
from typing import AsyncIterator

from ..core import (
    TRINO_URL, get_client, require_gateway_auth
)

router = APIRouter(
    prefix="/v1",
    tags=["Trino"],
    dependencies=[Depends(require_gateway_auth)],
)

@router.api_route("/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE","HEAD","OPTIONS"])
async def proxy_v1(path: str, request: Request, user: str = Depends(require_gateway_auth)):
    c: httpx.AsyncClient = await get_client()

    target = f"{TRINO_URL}/v1/{path}"
    if request.url.query:
        target = f"{target}?{request.url.query}"

    body = await request.body() if request.method in ("POST","PUT","PATCH") else None
    headers = forward_request_headers(request, user)

    r: httpx.Response = await c.request(
        method=request.method,
        url=target,
        headers=headers,
        content=body
    )

    ct = r.headers.get("content-type", "")
    if "application/json" in ct:
        try:
            payload = r.json()
            payload = rewrite_trino_uris(payload, TRINO_URL, gateway_base(request))
            pass_headers = {k: v for k, v in r.headers.items() if k.lower().startswith("x-trino-")}
            return JSONResponse(payload, status_code=r.status_code, headers=pass_headers)
        except ValueError:
            pass

    async def gen() -> AsyncIterator[bytes]:
        async for chunk in r.aiter_bytes():
            yield chunk
    return StreamingResponse(gen(), status_code=r.status_code, media_type=ct)

def forward_request_headers(req: Request, user: str) -> dict:
    h = {"X-Trino-User": user}
    for k, v in req.headers.items():
        lk = k.lower()
        if lk.startswith("x-trino-") or lk in {
            "content-type", "accept", "user-agent", "accept-encoding", "x-requested-with"
        }:
            h[k] = v
    h.setdefault("X-Trino-Source", "maskql")
    return h

def gateway_base(req: Request) -> str:
    proto = req.headers.get("x-forwarded-proto") or req.url.scheme
    host = (req.headers.get("x-forwarded-host")
            or req.headers.get("host")
            or req.url.netloc)

    prefix = (req.headers.get("x-forwarded-prefix")
                or req.scope.get("root_path", "")
                or "")

    if prefix and not prefix.startswith("/"):
        prefix = "/" + prefix
    base = f"{proto}://{host}{prefix}"
    return base.rstrip("/")

def rewrite_trino_uris(payload: dict, backend_base: str, front_base: str) -> dict:
    def rw(val):
        if isinstance(val, str) and val.startswith(backend_base):
            return front_base + val[len(backend_base):]
        return val

    for key in ("nextUri", "infoUri", "partialCancelUri"):
        if key in payload:
            payload[key] = rw(payload[key])

    stats = payload.get("stats")
    if isinstance(stats, dict) and "uri" in stats:
        stats["uri"] = rw(stats["uri"])

    if isinstance(payload.get("links"), list):
        for link in payload["links"]:
            if isinstance(link, dict) and "url" in link:
                link["url"] = rw(link["url"])
    return payload