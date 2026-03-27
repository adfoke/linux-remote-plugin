import sqlite3
from datetime import datetime, timedelta, timezone

from linux_remote_tool.audit import AuditLogger


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


def test_audit_query_logs_with_pagination_and_time_range(monkeypatch, tmp_path):
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

    page_one = logger.query_logs(page=1, page_size=1)
    assert page_one["page"] == 1
    assert page_one["page_size"] == 1
    assert len(page_one["items"]) == 1

    start_time = (now - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    filtered = logger.query_logs(page=1, page_size=10, start_time=start_time)
    assert filtered["total"] == 1
    assert filtered["items"][0]["operation_type"] == "run_command"


def test_audit_query_logs_rejects_invalid_time_filter(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    AuditLogger._instance = None
    logger = AuditLogger()

    try:
        logger.query_logs(start_time="bad")
    except ValueError as exc:
        assert "非法时间格式" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_audit_query_logs_limit_controls_result_count(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    AuditLogger._instance = None
    logger = AuditLogger()

    logger.log("first", "test-server", {"seq": 1})
    logger.log("second", "test-server", {"seq": 2})
    logger.log("third", "test-server", {"seq": 3})

    result = logger.query_logs(limit=2)

    assert result["page"] == 1
    assert result["page_size"] == 2
    assert result["total"] == 3
    assert [item["operation_type"] for item in result["items"]] == ["third", "second"]
