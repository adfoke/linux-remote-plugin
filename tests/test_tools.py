from unittest.mock import MagicMock

from alma_linux_remote_plugin.tools import (
    download_file,
    get_audit_web_server_status,
    list_hosts,
    run_command,
    start_audit_web_server,
    stop_audit_web_server,
    test_connection as tool_test_connection,
    upload_file,
)


def test_test_connection_success(monkeypatch):
    mock_result = MagicMock()
    mock_result.success = True
    monkeypatch.setattr(
        "alma_linux_remote_plugin.tools.SessionManager.run_command",
        lambda *args, **kwargs: mock_result,
    )

    result = tool_test_connection("test-server")
    assert "连接成功" in result


def test_test_connection_failure(monkeypatch):
    mock_result = MagicMock()
    mock_result.success = False
    monkeypatch.setattr(
        "alma_linux_remote_plugin.tools.SessionManager.run_command",
        lambda *args, **kwargs: mock_result,
    )

    result = tool_test_connection("test-server")
    assert "连接失败" in result


def test_test_connection_exception(monkeypatch):
    def raise_exc(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("alma_linux_remote_plugin.tools.SessionManager.run_command", raise_exc)
    result = tool_test_connection("test-server")
    assert "连接异常" in result


def test_run_command(monkeypatch):
    mock_result = MagicMock()
    monkeypatch.setattr(
        "alma_linux_remote_plugin.tools.SessionManager.run_command",
        lambda *args, **kwargs: mock_result,
    )

    result = run_command("test-server", "ls")
    assert result == mock_result


def test_upload_file(monkeypatch):
    monkeypatch.setattr(
        "alma_linux_remote_plugin.tools.SessionManager.upload_file",
        lambda *args, **kwargs: "上传成功 local.sh → /tmp/remote.sh",
    )

    result = upload_file("test-server", "local.sh", "/tmp/remote.sh")
    assert "上传成功" in result


def test_download_file(monkeypatch):
    monkeypatch.setattr(
        "alma_linux_remote_plugin.tools.SessionManager.download_file",
        lambda *args, **kwargs: "下载成功 /remote.sh → local.sh",
    )

    result = download_file("test-server", "/remote.sh", "local.sh")
    assert "下载成功" in result


def test_list_hosts(monkeypatch):
    monkeypatch.setattr(
        "alma_linux_remote_plugin.tools.load_hosts",
        lambda: {"test-server": object()},
    )
    assert list_hosts() == ["test-server"]


def test_start_audit_web_server(monkeypatch):
    logger = MagicMock()
    logger.start_dashboard.return_value = "http://127.0.0.1:8765"
    logger.dashboard_status.return_value = {
        "running": True,
        "url": "http://127.0.0.1:8765",
        "host": "127.0.0.1",
        "port": 8765,
        "db_path": "/tmp/audit.db",
    }
    monkeypatch.setattr("alma_linux_remote_plugin.tools.AuditLogger", lambda: logger)

    result = start_audit_web_server()

    assert result["running"] is True
    assert result["url"] == "http://127.0.0.1:8765"


def test_stop_audit_web_server(monkeypatch):
    logger = MagicMock()
    logger.dashboard_status.return_value = {
        "running": False,
        "url": None,
        "host": "127.0.0.1",
        "port": 8765,
        "db_path": "/tmp/audit.db",
    }
    monkeypatch.setattr("alma_linux_remote_plugin.tools.AuditLogger", lambda: logger)

    result = stop_audit_web_server()

    logger.stop_dashboard.assert_called_once()
    assert result["running"] is False


def test_get_audit_web_server_status(monkeypatch):
    logger = MagicMock()
    logger.dashboard_status.return_value = {
        "running": False,
        "url": None,
        "host": "127.0.0.1",
        "port": 8765,
        "db_path": "/tmp/audit.db",
    }
    monkeypatch.setattr("alma_linux_remote_plugin.tools.AuditLogger", lambda: logger)

    result = get_audit_web_server_status()

    assert result["running"] is False
