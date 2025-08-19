from sqlmodel import select
from maskql.models import User, Rule
from maskql.schemas.user import UserCreate, UserPatch
from maskql.db import AsyncSessionLocal
from typing import Sequence, Optional

class UserService:
    
    @staticmethod
    async def list_all() -> Sequence[User]:
        async with AsyncSessionLocal() as session:
            result = await session.exec(select(User).order_by(User.username))
            return result.all()
        
    @staticmethod
    async def get(user_id: int) -> Optional[User]:
        async with AsyncSessionLocal() as session:
            return await session.get(User, user_id)
        
    @staticmethod
    async def get_by_name(username: int) -> Optional[User]:
        async with AsyncSessionLocal() as session:
            return (await session.exec(select(User).where(User.username == username))).one_or_none()
        
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
    async def delete(user_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            obj = await session.get(User, user_id)
            if not obj:
                return False
            await session.delete(obj)
            await session.commit()
            return True

    @staticmethod
    async def authenticate(username: str, password: str) -> User | None:
        async with AsyncSessionLocal() as s:
            user = (await s.exec(select(User).where(User.username == username))).first()
            return user if user and user.check_password(password) else None
    
    
    
