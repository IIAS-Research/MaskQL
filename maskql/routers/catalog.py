from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from maskql.deps import get_session
from maskql.models.catalog import Catalog, CatalogCreate, CatalogPatch

router = APIRouter(prefix="/catalogs", tags=["Catalogs"])

@router.post("", response_model=Catalog, status_code=status.HTTP_201_CREATED)
async def create_catalog(payload: CatalogCreate, session: AsyncSession = Depends(get_session)):
    obj = Catalog(**payload.model_dump())
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Catalog's name already taken")
    await session.refresh(obj)
    return obj

@router.get("", response_model=list[Catalog])
async def list_catalogs(session: AsyncSession = Depends(get_session), skip: int = 0, limit: int = 100):
    rows = (await session.execute(select(Catalog).offset(skip).limit(limit))).scalars().all()
    return rows

@router.get("/{catalog_id}", response_model=Catalog)
async def get_catalog(catalog_id: int, session: AsyncSession = Depends(get_session)):
    obj = await session.get(Catalog, catalog_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Unable to find catalog")
    return obj

@router.put("/{catalog_id}", response_model=Catalog)
async def replace_catalog(catalog_id: int, payload: CatalogCreate, session: AsyncSession = Depends(get_session)):
    obj = await session.get(Catalog, catalog_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Unable to find catalog")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Catalog's name already taken")
    await session.refresh(obj)
    return obj

@router.patch("/{catalog_id}", response_model=Catalog)
async def patch_catalog(catalog_id: int, payload: CatalogPatch, session: AsyncSession = Depends(get_session)):
    obj = await session.get(Catalog, catalog_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Unable to find catalog")
    changes = payload.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(obj, k, v)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Catalog's name already taken")
    await session.refresh(obj)
    return obj

@router.delete("/{catalog_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_catalog(catalog_id: int, session: AsyncSession = Depends(get_session)):
    obj = await session.get(Catalog, catalog_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Unable to find catalog")
    await session.delete(obj)
    await session.commit()
    return None
