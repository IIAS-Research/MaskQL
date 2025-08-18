from sqlmodel import select
from maskql.models.user import User
from maskql.schemas.user import UserCreate, UserPatch
from maskql.db import AsyncSessionLocal
from typing import Sequence

class UserService:
    
    @staticmethod
    async def list_all() -> Sequence[User]:
        async with AsyncSessionLocal() as session:
            result = await session.exec(select(User).order_by(User.name))
            return result.all()
        
    @staticmethod
    async def create_user(data: UserCreate) -> User:
        async with AsyncSessionLocal() as s:
            if (await s.exec(select(User).where(User.username == data.username))).first():
                raise ValueError("username déjà utilisé")
            user = User.create(username=data.username, password=data.password)
            s.add(user); await s.commit(); await s.refresh(user)
            return user

    @staticmethod
    async def patch_user(user_id: int, patch: UserPatch) -> User | None:
        async with AsyncSessionLocal() as s:
            user = await s.get(User, user_id)
            if not user: return None
            if patch.username is not None:
                user.username = patch.username
            if patch.password is not None:
                user.set_password(patch.password)
            await s.commit(); await s.refresh(user)
            return user

    @staticmethod
    async def authenticate(username: str, password: str) -> User | None:
        async with AsyncSessionLocal() as s:
            user = (await s.exec(select(User).where(User.username == username))).first()
            return user if user and user.check_password(password) else None
