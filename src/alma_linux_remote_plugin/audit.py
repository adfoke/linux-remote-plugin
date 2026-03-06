from __future__ import annotations

import json
import socket
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

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
        self.dashboard_host = cfg.dashboard_host
        self.dashboard_port = cfg.dashboard_port

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_lock = threading.Lock()

        self._dashboard_server: uvicorn.Server | None = None
        self._dashboard_thread: threading.Thread | None = None
        self._dashboard_url: str | None = None

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
        host_name: Optional[str] = None,
        operation_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        page = max(1, page)
        page_size = max(1, min(page_size, 200))

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

    def _create_dashboard_app(self) -> FastAPI:
        app = FastAPI(title="AI Audit Logs", docs_url=None, redoc_url=None)
        logger = self

        @app.get("/", response_class=HTMLResponse)
        def index():
            return _dashboard_html()

        @app.get("/api/logs")
        def api_logs(
            page: int = Query(1, ge=1),
            page_size: int = Query(50, ge=1, le=200),
            host_name: Optional[str] = Query(None),
            operation_type: Optional[str] = Query(None),
            start_time: Optional[str] = Query(None),
            end_time: Optional[str] = Query(None),
        ):
            return logger.query_logs(
                page=page,
                page_size=page_size,
                host_name=host_name,
                operation_type=operation_type,
                start_time=start_time,
                end_time=end_time,
            )

        return app

    def start_dashboard(self, host: Optional[str] = None, port: Optional[int] = None) -> str:
        if self._dashboard_server is not None and self._dashboard_url is not None:
            return self._dashboard_url

        bind_host = host or self.dashboard_host
        bind_port = self.dashboard_port if port is None else port
        if bind_port == 0:
            bind_port = _find_free_port(bind_host)

        app = self._create_dashboard_app()
        config = uvicorn.Config(app, host=bind_host, port=bind_port, log_level="warning")
        server = uvicorn.Server(config)

        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        for _ in range(100):
            if server.started:
                break
            time.sleep(0.05)

        if not server.started:
            server.should_exit = True
            thread.join(timeout=5)
            raise RuntimeError("审计日志 Web 服务启动失败")

        self._dashboard_server = server
        self._dashboard_thread = thread
        self._dashboard_url = f"http://{bind_host}:{bind_port}"
        return self._dashboard_url

    def stop_dashboard(self):
        if self._dashboard_server is None:
            return

        self._dashboard_server.should_exit = True
        if self._dashboard_thread is not None:
            self._dashboard_thread.join(timeout=5)

        self._dashboard_server = None
        self._dashboard_thread = None
        self._dashboard_url = None

    def dashboard_status(self) -> Dict[str, Any]:
        running = bool(
            self._dashboard_server is not None
            and self._dashboard_thread is not None
            and self._dashboard_thread.is_alive()
            and self._dashboard_server.started
            and not self._dashboard_server.should_exit
            and self._dashboard_url is not None
        )
        return {
            "running": running,
            "url": self._dashboard_url if running else None,
            "host": self.dashboard_host,
            "port": self.dashboard_port,
            "db_path": str(self.db_path),
        }


def _find_free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _normalize_iso8601(value: str) -> str:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _dashboard_html() -> str:
    return """<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>AI Audit Logs</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; margin: 20px; }
    h1 { margin-bottom: 8px; }
    .controls { margin-bottom: 12px; display: flex; flex-wrap: wrap; gap: 8px; }
    input, button { padding: 6px 8px; }
    .meta { margin: 10px 0; color: #444; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #ddd; padding: 8px; font-size: 13px; vertical-align: top; }
    th { background: #f6f6f6; }
    code { white-space: pre-wrap; word-break: break-word; }
  </style>
</head>
<body>
  <h1>AI 操作审计日志</h1>
  <div class=\"controls\">
    <input id=\"host\" placeholder=\"host_name\" />
    <input id=\"op\" placeholder=\"operation_type\" />
    <input id=\"start\" placeholder=\"start_time (ISO8601)\" />
    <input id=\"end\" placeholder=\"end_time (ISO8601)\" />
    <input id=\"page\" type=\"number\" value=\"1\" min=\"1\" />
    <input id=\"pageSize\" type=\"number\" value=\"50\" min=\"1\" max=\"200\" />
    <button onclick=\"loadLogs()\">查询</button>
  </div>
  <div class=\"meta\" id=\"meta\"></div>
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>时间</th>
        <th>主机</th>
        <th>操作</th>
        <th>详情</th>
      </tr>
    </thead>
    <tbody id=\"logs\"></tbody>
  </table>

  <script>
    async function loadLogs() {
      const host = document.getElementById('host').value.trim();
      const op = document.getElementById('op').value.trim();
      const start = document.getElementById('start').value.trim();
      const end = document.getElementById('end').value.trim();
      const page = document.getElementById('page').value || '1';
      const pageSize = document.getElementById('pageSize').value || '50';

      const qs = new URLSearchParams({ page, page_size: pageSize });
      if (host) qs.set('host_name', host);
      if (op) qs.set('operation_type', op);
      if (start) qs.set('start_time', start);
      if (end) qs.set('end_time', end);

      const resp = await fetch('/api/logs?' + qs.toString());
      const data = await resp.json();

      document.getElementById('meta').innerText =
        `第 ${data.page} 页 / 共 ${data.total_pages} 页，${data.total} 条记录`;

      const tbody = document.getElementById('logs');
      tbody.innerHTML = '';
      (data.items || []).forEach(log => {
        const copy = { ...log };
        delete copy.id;
        delete copy.timestamp;
        delete copy.host_name;
        delete copy.operation_type;

        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${log.id}</td>
          <td>${log.timestamp}</td>
          <td>${log.host_name}</td>
          <td>${log.operation_type}</td>
          <td><code>${JSON.stringify(copy, null, 2)}</code></td>
        `;
        tbody.appendChild(tr);
      });
    }

    loadLogs();
  </script>
</body>
</html>
"""
