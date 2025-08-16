# app.py
import os, json
from typing import Optional, AsyncIterator
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import httpx

TRINO_URL = os.getenv("TRINO_URL", "http://trino:8080").rstrip("/")
CONNECT_TIMEOUT = float(os.getenv("CONNECT_TIMEOUT", "10"))
READ_TIMEOUT = float(os.getenv("READ_TIMEOUT", "3600"))
MAX_CONN = int(os.getenv("MAX_CONN", "200"))
MAX_KEEPALIVE = int(os.getenv("MAX_KEEPALIVE", "50"))

# TODO -> Real Auth
DEMO_USER = [("admin", "admin"), ("test", "test")]

# Forward all X-Trino-* and qqs headers
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
    # ex: "https://maskql.local:8443"
    return str(req.base_url).rstrip("/")

def rewrite_trino_uris(payload: dict, backend_base: str, front_base: str) -> dict:
    def rw(val: Optional[str]) -> Optional[str]:
        if isinstance(val, str) and val.startswith(backend_base):
            return front_base + val[len(backend_base):]
        return val

    for key in ("nextUri", "infoUri", "partialCancelUri"):
        if key in payload:
            payload[key] = rw(payload[key])

    stats = payload.get("stats")
    if isinstance(stats, dict) and "uri" in stats:
        stats["uri"] = rw(stats["uri"])

    # In case of links
    if isinstance(payload.get("links"), list):
        for link in payload["links"]:
            if isinstance(link, dict) and "url" in link:
                link["url"] = rw(link["url"])
    return payload

app = FastAPI(title="MaskQL Gateway", version="0.1")
security = HTTPBasic()

_client: Optional[httpx.AsyncClient] = None
async def client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(CONNECT_TIMEOUT, read=READ_TIMEOUT),
            limits=httpx.Limits(max_connections=MAX_CONN, max_keepalive_connections=MAX_KEEPALIVE),
            http2=False,  # Trino use HTTP/1.1
        )
    return _client

@app.on_event("shutdown")
async def _shutdown():
    global _client
    if _client:
        await _client.aclose()
        _client = None

async def require_auth(creds: HTTPBasicCredentials = Depends(security)) -> str:
    for user, password in DEMO_USER:
        if creds.username == user and creds.password == password:
            return creds.username
    raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# ── ALL routes beggining by /v1/ is forwarded to Trino (GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS)
@app.api_route("/v1/{path:path}",
        methods=["GET","POST","PUT","PATCH","DELETE","HEAD","OPTIONS"])
async def proxy_v1(path: str, request: Request, user: str = Depends(require_auth)):
    c = await client()

    # Build l’URL backend + querystring
    target = f"{TRINO_URL}/v1/{path}"
    if request.url.query:
        target = f"{target}?{request.url.query}"

    # Corps
    body = await request.body() if request.method in ("POST","PUT","PATCH") else None

    # Header to forward
    headers = forward_request_headers(request, user)

    # Call backend
    r: httpx.Response = await c.request(
        method=request.method,
        url=target,
        headers=headers,
        content=body
    )

    # Rewrite URI is JSON (Trino return JSON)
    ct = r.headers.get("content-type", "")
    if "application/json" in ct:
        try:
            payload = r.json()
            payload = rewrite_trino_uris(payload, TRINO_URL, gateway_base(request))
            pass_headers = {k: v for k, v in r.headers.items() if k.lower().startswith("x-trino-")}
            return JSONResponse(payload, status_code=r.status_code, headers=pass_headers)
        except ValueError:
            # Bad JSON
            pass

    # Else : raw streaming (usefull if Trino return something else)
    async def gen() -> AsyncIterator[bytes]:
        async for chunk in r.aiter_bytes():
            yield chunk
    return StreamingResponse(gen(), status_code=r.status_code, media_type=ct)
