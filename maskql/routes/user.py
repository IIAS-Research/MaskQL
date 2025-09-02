from fastapi import APIRouter, HTTPException, Depends
from maskql.schemas.user import UserCreate, UserRead, UserPatch
from maskql.services.user_service import UserService
from maskql.core import require_admin_token

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_admin_token)])

@router.get("", response_model=list[UserRead])
async def list_users():
    users = await UserService.list_all()
    return [UserRead.model_validate(u) for u in users]

@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int):
    obj = await UserService.get(user_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    return UserRead.model_validate(obj)

@router.post("", response_model=UserRead, status_code=201)
async def register_user(payload: UserCreate):
    try:
        user = await UserService.create_user(payload)
        return UserRead.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{user_id}", response_model=UserRead)
async def patch_user(user_id: int, payload: UserPatch):
    user = await UserService.patch_user(user_id, payload)
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
    return UserRead.model_validate(user)

@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int):
    ok = await UserService.delete(user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
