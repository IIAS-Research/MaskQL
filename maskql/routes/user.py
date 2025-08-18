from fastapi import APIRouter, HTTPException
from maskql.schemas.user import UserCreate, UserRead, UserPatch
from maskql.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_model=list[UserRead])
async def list_users():
    users = await UserService.list_all()
    return [UserRead.model_validate(u) for u in users]

@router.post("", response_model=UserRead, status_code=201)
async def register(payload: UserCreate):
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
