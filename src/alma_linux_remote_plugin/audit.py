from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .config import load_audit_config


class AuditLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_logger()
        return cls._instance

    def _init_logger(self):
        cfg = load_audit_config("hosts.yaml")
        self.enabled = cfg.enabled
        self.db_path = Path(cfg.db_path).expanduser().resolve()

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_lock = threading.Lock()

        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    host_name TEXT NOT NULL,
                    user TEXT NOT NULL,
                    details_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_host ON audit_logs(host_name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_operation ON audit_logs(operation_type)"
            )
            conn.commit()

    def log(self, operation_type: str, host_name: str, details: Dict[str, Any]):
        if not self.enabled:
            return

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "operation_type": operation_type,
            "host_name": host_name,
            "user": "AI_Agent",
            "details": details,
        }

        self._init_db()
        with self._db_lock:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    """
                    INSERT INTO audit_logs (timestamp, operation_type, host_name, user, details_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        record["timestamp"],
                        record["operation_type"],
                        record["host_name"],
                        record["user"],
                        json.dumps(record["details"], ensure_ascii=False),
                    ),
                )
                conn.commit()

    def query_logs(
        self,
        page: int = 1,
        page_size: int = 50,
        latest: int | None = None,
        host_name: Optional[str] = None,
        operation_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        page = max(1, page)
        page_size = max(1, min(page_size, 200))
        if latest is not None:
            page = 1
            page_size = max(1, min(latest, 200))

        normalized_start = _normalize_iso8601(start_time) if start_time else None
        normalized_end = _normalize_iso8601(end_time) if end_time else None

        conditions: list[str] = []
        params: list[Any] = []

        if host_name:
            conditions.append("host_name = ?")
            params.append(host_name)

        if operation_type:
            conditions.append("operation_type = ?")
            params.append(operation_type)

        if normalized_start:
            conditions.append("timestamp >= ?")
            params.append(normalized_start)

        if normalized_end:
            conditions.append("timestamp <= ?")
            params.append(normalized_end)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        self._init_db()
        with sqlite3.connect(str(self.db_path)) as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM audit_logs {where_clause}", params
            ).fetchone()[0]

            offset = (page - 1) * page_size
            rows = conn.execute(
                f"""
                SELECT id, timestamp, operation_type, host_name, user, details_json
                FROM audit_logs
                {where_clause}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()

        items: list[Dict[str, Any]] = []
        for row in rows:
            try:
                details = json.loads(row[5]) if row[5] else {}
            except json.JSONDecodeError:
                details = {"raw_details": row[5]}

            items.append(
                {
                    "id": row[0],
                    "timestamp": row[1],
                    "operation_type": row[2],
                    "host_name": row[3],
                    "user": row[4],
                    **details,
                }
            )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "items": items,
        }


def _normalize_iso8601(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"非法时间格式: {value}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")
