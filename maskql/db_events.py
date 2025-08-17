"""
    Catch data change in DB to trigger sync with Trino
"""
import asyncio
import logging
from sqlalchemy import event
from sqlalchemy.orm import Session
from maskql.models.catalog import Catalog

async def on_catalog_change():
    await Catalog.refresh_in_trino()

@event.listens_for(Session, "before_flush")
def _flag_catalog_change(session: Session, flush_ctx, instances):
    # If insert/update/delete on Catalog -> add a flag
    touched = (
        any(isinstance(o, Catalog) for o in session.new) or
        any(isinstance(o, Catalog) for o in session.dirty) or
        any(isinstance(o, Catalog) for o in session.deleted)
    )
    if touched:
        session.info["catalog_touched"] = True

@event.listens_for(Session, "after_commit")
def _trigger_after_commit(session: Session):
    # Trigger if something changed in catalog
    if not session.info.pop("catalog_touched", False):
        return
    # Link event and task
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(on_catalog_change())
    except RuntimeError:
        asyncio.run(on_catalog_change())

@event.listens_for(Session, "after_rollback")
def _clear_after_rollback(session: Session):
    session.info.pop("catalog_touched", None)
