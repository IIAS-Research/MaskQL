from fastapi import FastAPI
from maskql.core import close_client
from maskql.routers import acl
from maskql.routers import trino_proxy
from maskql.routers import catalog
import maskql.db_events
from maskql.models.catalog import Catalog


import logging, sys
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])

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
app.include_router(catalog.router)

# Init catalogs in Trino
Catalog.refresh_in_trino()

