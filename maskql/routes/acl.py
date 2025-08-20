from fastapi import APIRouter, Path, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from maskql.models import User
from maskql.services.user_service import UserService

router = APIRouter(
    prefix="/acl",
    tags=["ACL"],
    # dependencies=[Depends(require_auth)], # TODO No auth but this route must be available only for Trino
)

class CatalogsIn(BaseModel):
    catalogs: List[str] = Field(..., example=["biology", "test_db"])
class SchemasIn(BaseModel):
    schemas: List[str] = Field(..., example=["core", "domino"])
class TablesIn(BaseModel):
    tables: List[str] = Field(..., example=["user", "fiche", "stay"])
class ColumnsIn(BaseModel):
    columns: List[str] = Field(..., example=["name", "mail", "phone"])

@router.post("/{user}/catalog", response_model=List[str])
async def catalogs(
    user: str = Path(..., min_length=1),
    body: CatalogsIn = ...
) -> List[str]:
    user = await UserService.get_by_name(user)
    if not user:
        return []
    else:
        return await user.is_allowed(body.catalogs)

@router.post("/{user}/{catalog}/schemas", response_model=List[str])
async def schemas(
    user: str = Path(..., min_length=1),
    catalog: str = Path(..., min_length=1),
    body: SchemasIn = ...
) -> List[str]:
    user = await UserService.get_by_name(user)
    if not user:
        return []
    else:
        return await user.is_allowed(body.schemas, path=(catalog,))

@router.post("/{user}/{catalog}/tables", response_model=List[str])
async def tables(
    user: str = Path(..., min_length=1),
    catalog: str = Path(..., min_length=1),
    schema: Optional[str] = Query(None, description="Optional Schema"),
    body: TablesIn = ...
) -> List[str]:
    user = await UserService.get_by_name(user)
    if not user:
        return []
    else:
        return await user.is_allowed(body.tables, path=(catalog, schema))

@router.post("/{user}/{catalog}/{table}/columns", response_model=List[str])
async def columns(
    user: str = Path(..., min_length=1),
    catalog: str = Path(..., min_length=1),
    table: str = Path(..., min_length=1),
    schema: Optional[str] = Query(None, description="Optional Schema"),
    body: ColumnsIn = ...
) -> Dict:
    user = await UserService.get_by_name(user)
    if not user:
        return []
    else:
        return await user.is_allowed(body.columns, path=(catalog, schema, table))

@router.post("/{user}/{catalog}/{table}/row_filter", response_model=Dict)
async def row_filter(
    user: str = Path(..., min_length=1),
    catalog: str = Path(..., min_length=1),
    table: str = Path(..., min_length=1),
    schema: Optional[str] = Query(None, description="Optional Schema"),
) -> Dict:
    user = await UserService.get_by_name(user)
    if not user:
        return {"filter": "false"}
    else:
        return {"filter": (await user.row_filter(catalog, table, schema=schema) or "")}

@router.post("/{user}/{catalog}/{table}/{column}/mask", response_model=Dict)
async def mask(
    user: str = Path(..., min_length=1),
    catalog: str = Path(..., min_length=1),
    table: str = Path(..., min_length=1),
    column: str = Path(..., min_length=1),
    schema: Optional[str] = Query(None, description="Optional Schema"),
) -> Dict:
    user = await UserService.get_by_name(user)
    if not user:
        return {"mask": ""}
    else:
        return {"mask": (await user.mask(catalog, table, column, schema=schema)) or ""}

@router.post("/{user}/{catalog}/can_access", response_model=dict)
async def can_access_catalog(
    user: str = Path(..., min_length=1),
    catalog: str = Path(..., min_length=1),
) -> dict:
    user = await UserService.get_by_name(user)
    if not user:
        return {"allowed": False}
    else:
        return {"allowed": catalog in (await user.is_allowed([catalog]))}

