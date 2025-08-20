# maskql/routers/rule_router.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from maskql.schemas.rule import RuleCreate, RuleRead, RulePatch
from maskql.services.rule_service import RuleService
from maskql.core import require_admin_auth

router = APIRouter(
    prefix="/rules",
    tags=["rules"],
    dependencies=[Depends(require_admin_auth)]
)

@router.get("", response_model=list[RuleRead])
async def list_rules():
    rules = await RuleService.list_all()
    return [RuleRead.model_validate(r) for r in rules]

@router.get("/{rule_id}", response_model=RuleRead)
async def get_rule(rule_id: int):
    rule = await RuleService.get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Not found")
    return RuleRead.model_validate(rule)

@router.post("", response_model=RuleRead, status_code=201)
async def create_rule(payload: RuleCreate):
    try:
        rule = await RuleService.create(payload)
        return RuleRead.model_validate(rule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{rule_id}", response_model=RuleRead)
async def patch_rule(rule_id: int, payload: RulePatch):
    try:
        rule = await RuleService.patch(rule_id, payload)
        if not rule:
            raise HTTPException(status_code=404, detail="Not found")
        return RuleRead.model_validate(rule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: int):
    ok = await RuleService.delete(rule_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")
