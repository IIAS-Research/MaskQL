from fastapi import APIRouter, Path, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

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
    return body.catalogs

@router.post("/{user}/{catalog}/schemas", response_model=List[str])
async def schemas(
    user: str = Path(..., min_length=1),
    catalog: str = Path(..., min_length=1),
    body: SchemasIn = ...
) -> List[str]:
    return body.schemas

@router.post("/{user}/{catalog}/tables", response_model=List[str])
async def tables(
    user: str = Path(..., min_length=1),
    catalog: str = Path(..., min_length=1),
    schema: Optional[str] = Query(None, description="Optional Schema"),
    body: TablesIn = ...
) -> List[str]:
    return body.tables

@router.post("/{user}/{catalog}/{table}/is_columns_allowed", response_model=Dict)
async def is_columns_allowed(
    user: str = Path(..., min_length=1),
    catalog: str = Path(..., min_length=1),
    table: str = Path(..., min_length=1),
    schema: Optional[str] = Query(None, description="Optional Schema"),
    body: ColumnsIn = ...
) -> Dict:
    return {"allowed": True}

@router.post("/{user}/{catalog}/{table}/row_filters", response_model=Dict)
async def row_filter(
    user: str = Path(..., min_length=1),
    catalog: str = Path(..., min_length=1),
    table: str = Path(..., min_length=1),
    schema: Optional[str] = Query(None, description="Optional Schema"),
) -> Dict:
    return {"filters": []}

@router.post("/{user}/{catalog}/{table}/{column}/mask", response_model=Dict)
async def mask(
    user: str = Path(..., min_length=1),
    catalog: str = Path(..., min_length=1),
    table: str = Path(..., min_length=1),
    column: str = Path(..., min_length=1),
    schema: Optional[str] = Query(None, description="Optional Schema"),
) -> Dict:
    if user == "test" and catalog == "test_db" and table == "client" and column == "name":
        return {"mask": "CASE WHEN name IS NULL THEN NULL WHEN length(name) <= 2 THEN name ELSE rpad(substring(name, 1, 2), length(name), '*') END"}
    return {"mask": column}

@router.post("/{user}/{catalog}/can_access", response_model=dict)
async def can_access_catalog(
    user: str = Path(..., min_length=1),
    catalog: str = Path(..., min_length=1),
) -> dict:
    return {"allowed": True}

