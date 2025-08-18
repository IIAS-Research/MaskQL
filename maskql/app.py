from fastapi import FastAPI
from maskql.core import close_client

from maskql.routes import acl
from maskql.routes import trino_proxy
from maskql.routes import catalog
from maskql.routes import user

from maskql.services.catalog_service import CatalogService


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
app.include_router(user.router)

# Init catalogs in Trino
CatalogService.refresh_in_trino()

