from unittest.mock import patch

import pytest

from alma_linux_remote_plugin.runtime_adapter import adapter


def test_get_tools():
    tools = adapter.get_tools()
    assert len(tools) == 8


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


@patch("alma_linux_remote_plugin.runtime_adapter.upload_file")
def test_invoke_upload_file(mock_upload):
    mock_upload.return_value = "ok"
    result = adapter.invoke(
        "upload_file",
        {"host_name": "h", "local_path": "l", "remote_path": "r"},
    )
    assert result == "ok"


@patch("alma_linux_remote_plugin.runtime_adapter.start_audit_web_server")
def test_invoke_start_audit_web_server(mock_start):
    mock_start.return_value = {"running": True, "url": "http://127.0.0.1:8765"}

    result = adapter.invoke("start_audit_web_server", {})

    assert result["running"] is True


@patch("alma_linux_remote_plugin.runtime_adapter.stop_audit_web_server")
def test_invoke_stop_audit_web_server(mock_stop):
    mock_stop.return_value = {"running": False, "url": None}

    result = adapter.invoke("stop_audit_web_server", {})

    assert result["running"] is False


@patch("alma_linux_remote_plugin.runtime_adapter.get_audit_web_server_status")
def test_invoke_get_audit_web_server_status(mock_status):
    mock_status.return_value = {"running": False, "url": None}

    result = adapter.invoke("get_audit_web_server_status", {})

    assert result["running"] is False


def test_invoke_unknown_tool():
    with pytest.raises(ValueError, match="未知工具"):
        adapter.invoke("unknown", {})
