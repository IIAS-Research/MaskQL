from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Response, status

from maskql.schemas.catalog import CatalogCreate, CatalogPatch, CatalogRead, CatalogConnectionStatusRead
from maskql.services.catalog_service import CatalogService
from maskql.core import require_admin_token

router = APIRouter(
    prefix="/catalogs", 
    tags=["catalogs"],
    dependencies=[Depends(require_admin_token)]
    )

@router.get("", response_model=list[CatalogRead])
async def list_catalogs():
    rows = await CatalogService.list_all()
    return [CatalogRead.model_validate(r) for r in rows]


@router.get("/status", response_model=list[CatalogConnectionStatusRead])
async def list_catalog_statuses():
    return await CatalogService.list_connection_statuses()

@router.get("/{catalog_id}", response_model=CatalogRead)
async def get_catalog(catalog_id: int):
    obj = await CatalogService.get(catalog_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Catalog not found")
    return CatalogRead.model_validate(obj)

@router.post("", response_model=CatalogRead, status_code=status.HTTP_201_CREATED)
async def create_catalog(payload: CatalogCreate):
    try:
        obj = await CatalogService.create(payload)
        return CatalogRead.model_validate(obj)
    except ValueError as e:
        # ex: nom déjà utilisé
        raise HTTPException(status_code=409, detail=str(e))

@router.patch("/{catalog_id}", response_model=CatalogRead)
async def patch_catalog(catalog_id: int, payload: CatalogPatch):
    try:
        obj = await CatalogService.patch(catalog_id, payload)
        if not obj:
            raise HTTPException(status_code=404, detail="Catalog not found")
        return CatalogRead.model_validate(obj)
    except Exception as e:
        # ex: nom déjà utilisé
        raise HTTPException(status_code=409, detail=str(e))

@router.delete("/{catalog_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_catalog(catalog_id: int):
    ok = await CatalogService.delete(catalog_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Catalog not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/refresh-trino")
async def refresh_trino():
    """
    Synchronise les catalogs Trino avec ceux stockés en base.
    Retourne { dropped: [...], created: [...] }.
    """
    result = await CatalogService.refresh_in_trino()
    return result
