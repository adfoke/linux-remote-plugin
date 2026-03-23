from unittest.mock import patch

import pytest

from alma_linux_remote_plugin.runtime_adapter import adapter


def test_get_tools():
    tools = adapter.get_tools()
    assert len(tools) == 10


@patch("alma_linux_remote_plugin.runtime_adapter.list_hosts")
def test_invoke_list_hosts(mock_list_hosts):
    mock_list_hosts.return_value = ["test-server"]
    result = adapter.invoke("list_hosts", {})
    assert result == ["test-server"]


@patch("alma_linux_remote_plugin.runtime_adapter.run_command")
def test_invoke_run_command(mock_run_command):
    mock_result = type("R", (), {"model_dump": lambda self: {"success": True}})()
    mock_run_command.return_value = mock_result

    result = adapter.invoke(
        "run_command",
        {
            "host_name": "test-server",
            "command": "uptime",
        },
    )
    assert result["success"] is True


@patch("alma_linux_remote_plugin.runtime_adapter.test_connection_batch")
def test_invoke_test_connection_batch(mock_test_connection_batch):
    mock_result = type(
        "R",
        (),
        {
            "model_dump": lambda self: {
                "total": 2,
                "success_count": 1,
                "failure_count": 1,
                "items": [
                    {"host_name": "h1", "success": True, "message": "h1 连接成功"},
                    {"host_name": "h2", "success": False, "message": "h2 连接失败"},
                ],
            }
        },
    )()
    mock_test_connection_batch.return_value = mock_result

    result = adapter.invoke(
        "test_connection_batch",
        {
            "host_names": ["h1", "h2"],
        },
    )
    assert result["total"] == 2
    assert result["failure_count"] == 1


@patch("alma_linux_remote_plugin.runtime_adapter.run_command_batch")
def test_invoke_run_command_batch(mock_run_command_batch):
    mock_result = type(
        "R",
        (),
        {
            "model_dump": lambda self: {
                "total": 2,
                "success_count": 2,
                "failure_count": 0,
                "items": [],
            }
        },
    )()
    mock_run_command_batch.return_value = mock_result

    result = adapter.invoke(
        "run_command_batch",
        {
            "host_names": ["test-server-1", "test-server-2"],
            "command": "uptime",
        },
    )
    assert result["total"] == 2


@patch("alma_linux_remote_plugin.runtime_adapter.upload_file")
def test_invoke_upload_file(mock_upload):
    mock_upload.return_value = "ok"
    result = adapter.invoke(
        "upload_file",
        {"host_name": "h", "local_path": "l", "remote_path": "r"},
    )
    assert result == "ok"


@patch("alma_linux_remote_plugin.runtime_adapter.upload_file_batch")
def test_invoke_upload_file_batch(mock_upload_file_batch):
    mock_upload_file_batch.return_value = type(
        "R",
        (),
        {
            "model_dump": lambda self: {
                "total": 2,
                "success_count": 2,
                "failure_count": 0,
                "items": [],
            }
        },
    )()

    result = adapter.invoke(
        "upload_file_batch",
        {
            "host_names": ["h1", "h2"],
            "local_path": "a.txt",
            "remote_path": "/tmp/a.txt",
        },
    )
    assert result["success_count"] == 2


@patch("alma_linux_remote_plugin.runtime_adapter.download_file_batch")
def test_invoke_download_file_batch(mock_download_file_batch):
    mock_download_file_batch.return_value = type(
        "R",
        (),
        {
            "model_dump": lambda self: {
                "total": 2,
                "success_count": 1,
                "failure_count": 1,
                "items": [],
            }
        },
    )()

    result = adapter.invoke(
        "download_file_batch",
        {
            "host_names": ["h1", "h2"],
            "remote_path": "/remote.sh",
            "local_path_template": "/tmp/{host_name}-remote.sh",
        },
    )
    assert result["failure_count"] == 1


@patch("alma_linux_remote_plugin.runtime_adapter.query_audit_logs")
def test_invoke_query_audit_logs(mock_query_audit_logs):
    mock_query_audit_logs.return_value = {
        "page": 1,
        "page_size": 2,
        "total": 2,
        "total_pages": 1,
        "items": [{"id": 2}, {"id": 1}],
    }

    result = adapter.invoke(
        "query_audit_logs",
        {
            "latest": 2,
            "host_name": "test-server",
        },
    )

    mock_query_audit_logs.assert_called_once_with(
        page=1,
        latest=2,
        host_name="test-server",
        operation_type=None,
        start_time=None,
        end_time=None,
    )
    assert result["total"] == 2


def test_invoke_unknown_tool():
    with pytest.raises(ValueError, match="未知工具"):
        adapter.invoke("unknown", {})
