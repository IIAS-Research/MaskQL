from __future__ import annotations

import os
from typing import Any, Dict, Optional
import httpx

import logging
log = logging.getLogger("maskql.db_events")


async def trino_sql(
    sql: str,
    *,
    base: Optional[str] = None,
    user: Optional[str] = None,
    source: Optional[str] = None,
    timeout: float = 30.0,
    follow_next: bool = True,
) -> Dict[str, Any]:
    """
    Run SQL directly on Trino (no gateway)
    """
    base_url = base or os.getenv("TRINO_URL", "http://trino:8080")
    headers = {
        "X-Trino-User": user or os.getenv("TRINO_USER", "maskql-admin"), # maskql-admin is known by maskql-acl and allow to create catalog
        "X-Trino-Source": source or os.getenv("TRINO_SOURCE", "maskql-admin"),
    }
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        # POST initial
        resp = await client.post(f"{base_url}/v1/statement", headers=headers, content=sql)
        resp.raise_for_status()
        payload = resp.json()

        # Loop on nextUri
        next_uri = payload.get("nextUri")
        while follow_next and next_uri:
            resp = await client.get(next_uri, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
            next_uri = payload.get("nextUri")

    # If error, propagate it
    if isinstance(payload, dict) and payload.get("error"):
        msg = payload["error"].get("message") or "Trino error"
        raise RuntimeError(msg)

    return payload


async def trino_ddl(sql: str, **kwargs) -> None:
    """Run a query DDL (CREATE/DROP/...) and ignore result rows"""
    await trino_sql(sql, **kwargs)