from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Response, status

from maskql.schemas.catalog import (
    CatalogTablePreviewRead,
    CatalogTablePreviewRequest,
    CatalogConnectionStatusRead,
    CatalogCreate,
    CatalogPatch,
    CatalogSchemaEntryCreate,
    CatalogRead,
    CatalogSchemaEntryRead,
    CatalogSchemaSyncRead,
)
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


@router.get("/{catalog_id}/schema", response_model=list[CatalogSchemaEntryRead])
async def list_catalog_schema(catalog_id: int):
    obj = await CatalogService.get(catalog_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Catalog not found")
    return await CatalogService.list_schema_entries(catalog_id)


@router.post("/{catalog_id}/schema", response_model=CatalogSchemaEntryRead, status_code=status.HTTP_201_CREATED)
async def create_catalog_schema_entry(catalog_id: int, payload: CatalogSchemaEntryCreate):
    obj = await CatalogService.get(catalog_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Catalog not found")
    try:
        return await CatalogService.create_manual_schema_entry(catalog_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{catalog_id}/schema/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_catalog_schema_entry(catalog_id: int, entry_id: int):
    obj = await CatalogService.get(catalog_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Catalog not found")
    try:
        ok = await CatalogService.delete_manual_schema_entry(catalog_id, entry_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Schema entry not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{catalog_id}/schema/sync", response_model=CatalogSchemaSyncRead)
async def sync_catalog_schema(catalog_id: int):
    obj = await CatalogService.get(catalog_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Catalog not found")
    try:
        return await CatalogService.sync_schema(catalog_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/{catalog_id}/schema/preview", response_model=CatalogTablePreviewRead)
async def preview_catalog_table(catalog_id: int, payload: CatalogTablePreviewRequest):
    try:
        return await CatalogService.preview_table(
            catalog_id,
            payload.user_id,
            payload.schema_name,
            payload.table_name,
            limit=payload.limit,
        )
    except ValueError as e:
        detail = str(e)
        status_code = 404 if detail in {"Catalog not found", "User not found"} else 400
        raise HTTPException(status_code=status_code, detail=detail)

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
