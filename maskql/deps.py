"""
FastAPI async DB dependency.

Exposes `get_session()`, which yields an `AsyncSession` per request and ensures
the session is closed/cleaned up after the response (even on errors). Use with
`Depends(get_session)` in your endpoints.
"""

from typing import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from .db import AsyncSessionLocal

async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session