import sqlite3
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen

from alma_linux_remote_plugin.audit import AuditLogger


def test_audit_logger_writes_sqlite(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    AuditLogger._instance = None
    logger = AuditLogger()
    logger.log("run_command", "test-server", {"success": True})

    db_file = tmp_path / "logs" / "audit.db"
    assert db_file.exists()

    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT operation_type, host_name, details_json FROM audit_logs ORDER BY id DESC LIMIT 1"
        ).fetchone()

    assert row is not None
    assert row[0] == "run_command"
    assert row[1] == "test-server"
    assert '"success": true' in row[2]


def test_audit_dashboard_api_with_pagination_and_time_range(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    AuditLogger._instance = None
    logger = AuditLogger()

    now = datetime.now(timezone.utc)
    old = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    new = (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")

    # 先造两条数据
    logger.log("upload_file", "test-server", {"remote_path": "/tmp/a"})
    logger.log("run_command", "test-server", {"command": "uptime"})

    # 手工把最早的一条时间改老，方便测试时间过滤
    db_file = tmp_path / "logs" / "audit.db"
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "UPDATE audit_logs SET timestamp = ? WHERE id = (SELECT MIN(id) FROM audit_logs)",
            (old,),
        )
        conn.execute(
            "UPDATE audit_logs SET timestamp = ? WHERE id = (SELECT MAX(id) FROM audit_logs)",
            (new,),
        )
        conn.commit()

    url = logger.start_dashboard(port=0)
    try:
        with urlopen(f"{url}/api/logs?page=1&page_size=1") as resp:
            body = resp.read().decode("utf-8")
        assert '"page":1' in body
        assert '"page_size":1' in body

        start_time = (now - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        with urlopen(f"{url}/api/logs?page=1&page_size=10&start_time={start_time}") as resp:
            body2 = resp.read().decode("utf-8")
        assert '"total":1' in body2
    finally:
        logger.stop_dashboard()


def test_audit_dashboard_status_defaults_to_stopped(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    AuditLogger._instance = None
    logger = AuditLogger()

    status = logger.dashboard_status()

    assert status["running"] is False
    assert status["url"] is None
    assert status["port"] == 8765
