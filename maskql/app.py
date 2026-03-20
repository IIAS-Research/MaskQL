from fastapi import FastAPI
import asyncio

from maskql.core import close_client

from maskql.routes import acl
from maskql.routes import trino_proxy
from maskql.routes import catalog
from maskql.routes import user
from maskql.routes import rule
from maskql.routes import admin_auth

from maskql.services.catalog_service import CatalogService


import logging, sys
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])

APP_VERSION = "1.1.0"

app = FastAPI(title="MaskQL Gateway", version=APP_VERSION)

@app.on_event("startup")
async def _startup():
    async def _trino_init():
        await asyncio.sleep(5)
        await CatalogService.refresh_in_trino()

    asyncio.create_task(_trino_init())
    
@app.on_event("shutdown")
async def _shutdown():
    await close_client()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# Plug routes
app.include_router(admin_auth.router)
app.include_router(acl.router)
app.include_router(trino_proxy.router)
app.include_router(catalog.router)
app.include_router(user.router)
app.include_router(rule.router)

