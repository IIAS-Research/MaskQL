from fastapi import FastAPI
from maskql.core import close_client
from maskql.routers import acl
from maskql.routers import trino_proxy

app = FastAPI(title="MaskQL Gateway", version="0.1")

@app.on_event("shutdown")
async def _shutdown():
    await close_client()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# Plug routes
app.include_router(acl.router)
app.include_router(trino_proxy.router)

