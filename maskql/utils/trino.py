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
    as_dicts: bool = False,
) -> Dict[str, Any]:
    """
    Run SQL directly on Trino (no gateway), en renvoyant les lignes.

    Retourne un dict avec:
      - id, infoUri
      - columns: liste des noms de colonnes
      - columns_meta: métadonnées "columns" originales de Trino
      - rows: liste des lignes (list[list[Any]] ou list[dict] si as_dicts=True)
      - rowcount: nombre total de lignes
      - stats, warnings
      - updateType / updateCount (si DDL/INSERT/UPDATE)
    """
    base_url = base or os.getenv("TRINO_URL", "http://trino:8080")
    headers = {
        "X-Trino-User": user or os.getenv("TRINO_USER", "maskql-admin"),
        "X-Trino-Source": source or os.getenv("TRINO_SOURCE", "maskql-admin"),
    }

    rows: List[List[Any]] = []
    columns_meta: List[Dict[str, Any]] = []
    column_names: List[str] = []
    first_payload: Dict[str, Any] | None = None
    last_payload: Dict[str, Any] | None = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(f"{base_url}/v1/statement", headers=headers, content=sql)
        resp.raise_for_status()
        payload = resp.json()
        first_payload = payload
        last_payload = payload

        if "columns" in payload and not columns_meta:
            columns_meta = payload["columns"]
            column_names = [c["name"] for c in columns_meta]
        if "data" in payload:
            rows.extend(payload["data"])

        next_uri = payload.get("nextUri")
        while follow_next and next_uri:
            resp = await client.get(next_uri, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
            last_payload = payload

            if isinstance(payload, dict) and payload.get("error"):
                msg = payload["error"].get("message") or "Trino error"
                raise RuntimeError(msg)

            if "columns" in payload and not columns_meta:
                columns_meta = payload["columns"]
                column_names = [c["name"] for c in columns_meta]
            if "data" in payload:
                rows.extend(payload["data"])

            next_uri = payload.get("nextUri")

    if isinstance(last_payload, dict) and last_payload.get("error"):
        msg = last_payload["error"].get("message") or "Trino error"
        raise RuntimeError(msg)

    result_rows = (
        [dict(zip(column_names, r)) for r in rows] if as_dicts and column_names else rows
    )

    return {
        "id": (first_payload or {}).get("id"),
        "infoUri": (first_payload or {}).get("infoUri"),
        "columns": column_names,
        "columns_meta": columns_meta,
        "rows": result_rows,
        "rowcount": len(rows),
        "stats": (last_payload or {}).get("stats", {}),
        "warnings": (last_payload or {}).get("warnings", []),
        "updateType": (last_payload or {}).get("updateType"),
        "updateCount": (last_payload or {}).get("updateCount"),
        "last_payload": last_payload,
    }


async def trino_ddl(sql: str, **kwargs) -> None:
    """Run a query DDL (CREATE/DROP/...) and ignore result rows"""
    await trino_sql(sql, **kwargs)