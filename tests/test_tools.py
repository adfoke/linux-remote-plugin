from unittest.mock import MagicMock

from linux_remote_tool.models import (
    BatchCommandItem,
    BatchCommandResult,
    BatchTransferItem,
    BatchTransferResult,
)
from linux_remote_tool.tools import (
    download_file,
    download_file_batch,
    list_hosts,
    query_audit_logs,
    run_command,
    run_command_batch,
    test_connection as tool_test_connection,
    test_connection_batch,
    upload_file_batch,
    upload_file,
)


def test_test_connection_success(monkeypatch):
    mock_result = MagicMock()
    mock_result.success = True
    monkeypatch.setattr(
        "linux_remote_tool.tools.SessionManager.run_command",
        lambda *args, **kwargs: mock_result,
    )

    result = tool_test_connection("test-server")
    assert "连接成功" in result


def test_test_connection_failure(monkeypatch):
    mock_result = MagicMock()
    mock_result.success = False
    monkeypatch.setattr(
        "linux_remote_tool.tools.SessionManager.run_command",
        lambda *args, **kwargs: mock_result,
    )

    result = tool_test_connection("test-server")
    assert "连接失败" in result


def test_test_connection_exception(monkeypatch):
    def raise_exc(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("linux_remote_tool.tools.SessionManager.run_command", raise_exc)
    result = tool_test_connection("test-server")
    assert "连接异常" in result


def test_test_connection_batch(monkeypatch):
    monkeypatch.setattr(
        "linux_remote_tool.tools.SessionManager.run_command_batch",
        lambda *args, **kwargs: BatchCommandResult(
            total=3,
            success_count=1,
            failure_count=2,
            items=[
                BatchCommandItem(
                    host_name="ok-host",
                    command="echo 'connected'",
                    exit_code=0,
                    stdout="connected",
                    stderr="",
                    success=True,
                ),
                BatchCommandItem(
                    host_name="fail-host",
                    command="echo 'connected'",
                    exit_code=1,
                    stdout="",
                    stderr="",
                    success=False,
                ),
                BatchCommandItem(
                    host_name="err-host",
                    command="echo 'connected'",
                    exit_code=255,
                    stdout="",
                    stderr="boom",
                    success=False,
                ),
            ],
        ),
    )

    result = test_connection_batch(["ok-host", "fail-host", "err-host"])

    assert result.total == 3
    assert result.success_count == 1
    assert result.failure_count == 2
    assert result.items[0].message == "ok-host 连接成功"
    assert result.items[1].message == "fail-host 连接失败"
    assert result.items[2].message == "err-host 连接异常: boom"


def test_run_command(monkeypatch):
    mock_result = MagicMock()
    monkeypatch.setattr(
        "linux_remote_tool.tools.SessionManager.run_command",
        lambda *args, **kwargs: mock_result,
    )

    result = run_command("test-server", "ls")
    assert result == mock_result


def test_run_command_batch(monkeypatch):
    mock_result = MagicMock()
    monkeypatch.setattr(
        "linux_remote_tool.tools.SessionManager.run_command_batch",
        lambda *args, **kwargs: mock_result,
    )

    result = run_command_batch(["test-server-1", "test-server-2"], "ls")

    assert result == mock_result


def test_upload_file(monkeypatch):
    monkeypatch.setattr(
        "linux_remote_tool.tools.SessionManager.upload_file",
        lambda *args, **kwargs: "上传成功 local.sh → /tmp/remote.sh",
    )

    result = upload_file("test-server", "local.sh", "/tmp/remote.sh")
    assert "上传成功" in result


def test_upload_file_batch(monkeypatch):
    monkeypatch.setattr(
        "linux_remote_tool.tools.SessionManager.upload_file_batch",
        lambda *args, **kwargs: BatchTransferResult(
            total=2,
            success_count=2,
            failure_count=0,
            items=[
                BatchTransferItem(
                    host_name="h1",
                    success=True,
                    message="上传成功 a.txt → /tmp/a.txt",
                    local_path="a.txt",
                    remote_path="/tmp/a.txt",
                ),
                BatchTransferItem(
                    host_name="h2",
                    success=True,
                    message="上传成功 a.txt → /tmp/a.txt",
                    local_path="a.txt",
                    remote_path="/tmp/a.txt",
                ),
            ],
        ),
    )

    result = upload_file_batch(["h1", "h2"], "a.txt", "/tmp/a.txt")

    assert result.total == 2


def test_download_file(monkeypatch):
    monkeypatch.setattr(
        "linux_remote_tool.tools.SessionManager.download_file",
        lambda *args, **kwargs: "下载成功 /remote.sh → local.sh",
    )

    result = download_file("test-server", "/remote.sh", "local.sh")
    assert "下载成功" in result


def test_download_file_batch(monkeypatch):
    monkeypatch.setattr(
        "linux_remote_tool.tools.SessionManager.download_file_batch",
        lambda *args, **kwargs: BatchTransferResult(
            total=2,
            success_count=1,
            failure_count=1,
            items=[
                BatchTransferItem(
                    host_name="h1",
                    success=True,
                    message="下载成功 /remote.sh → /tmp/h1-remote.sh",
                    local_path="/tmp/h1-remote.sh",
                    remote_path="/remote.sh",
                ),
                BatchTransferItem(
                    host_name="h2",
                    success=False,
                    message="下载失败 /remote.sh → /tmp/h2-remote.sh",
                    local_path="/tmp/h2-remote.sh",
                    remote_path="/remote.sh",
                    error="boom",
                ),
            ],
        ),
    )

    result = download_file_batch(["h1", "h2"], "/remote.sh", "/tmp/{host_name}-remote.sh")

    assert result.failure_count == 1


def test_list_hosts(monkeypatch):
    monkeypatch.setattr(
        "linux_remote_tool.tools.load_hosts",
        lambda: {"test-server": object()},
    )
    assert list_hosts() == ["test-server"]


def test_query_audit_logs(monkeypatch):
    logger = MagicMock()
    logger.query_logs.return_value = {
        "page": 1,
        "page_size": 50,
        "total": 1,
        "total_pages": 1,
        "items": [{"id": 1}],
    }
    monkeypatch.setattr("linux_remote_tool.tools.AuditLogger", lambda: logger)

    result = query_audit_logs(page=1, page_size=50, host_name="test-server")

    logger.query_logs.assert_called_once_with(
        page=1,
        page_size=50,
        limit=None,
        host_name="test-server",
        operation_type=None,
        start_time=None,
        end_time=None,
    )
    assert result["total"] == 1


def test_query_audit_logs_with_limit(monkeypatch):
    logger = MagicMock()
    logger.query_logs.return_value = {
        "page": 1,
        "page_size": 2,
        "total": 5,
        "total_pages": 3,
        "items": [{"id": 5}, {"id": 4}],
    }
    monkeypatch.setattr("linux_remote_tool.tools.AuditLogger", lambda: logger)

    result = query_audit_logs(limit=2)

    logger.query_logs.assert_called_once_with(
        page=1,
        page_size=50,
        limit=2,
        host_name=None,
        operation_type=None,
        start_time=None,
        end_time=None,
    )
    assert [item["id"] for item in result["items"]] == [5, 4]
