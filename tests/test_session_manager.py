from unittest.mock import MagicMock

import pytest

from alma_linux_remote_plugin.models import HostAuth, HostConfig
from alma_linux_remote_plugin.session_manager import SessionManager


def test_run_command_uses_cached_session(monkeypatch):
    SessionManager._sessions = {}
    SessionManager._cleanup_thread = None

    host_cfg = HostConfig(
        host="127.0.0.1",
        username="u",
        auth=HostAuth(method="key", key_path="~/.ssh/id_ed25519"),
    )
    monkeypatch.setattr("alma_linux_remote_plugin.session_manager.load_hosts", lambda: {"h": host_cfg})

    client = MagicMock()
    transport = MagicMock()
    transport.is_active.return_value = True
    client.get_transport.return_value = transport

    sftp = MagicMock()
    client.open_sftp.return_value = sftp

    stdout = MagicMock()
    stdout.read.return_value = b"ok"
    stdout.channel.recv_exit_status.return_value = 0
    stderr = MagicMock()
    stderr.read.return_value = b""
    client.exec_command.return_value = (None, stdout, stderr)

    monkeypatch.setattr("paramiko.SSHClient", lambda: client)
    monkeypatch.setattr("alma_linux_remote_plugin.session_manager.SSHManager._connect", lambda *args, **kwargs: None)

    r1 = SessionManager.run_command("h", "echo ok")
    r2 = SessionManager.run_command("h", "echo ok")

    assert r1.success is True
    assert r2.success is True
    assert len(SessionManager._sessions) == 1


def test_ensure_session_closes_stale_session_before_reconnect(monkeypatch):
    SessionManager._sessions = {}
    SessionManager._cleanup_thread = None

    host_cfg = HostConfig(
        host="127.0.0.1",
        username="u",
        auth=HostAuth(method="key", key_path="~/.ssh/id_ed25519"),
    )
    monkeypatch.setattr("alma_linux_remote_plugin.session_manager.load_hosts", lambda: {"h": host_cfg})
    monkeypatch.setattr(
        "alma_linux_remote_plugin.session_manager.SSHManager._connect",
        lambda *args, **kwargs: None,
    )

    old_client = MagicMock()
    old_transport = MagicMock()
    old_transport.is_active.return_value = False
    old_client.get_transport.return_value = old_transport
    old_sftp = MagicMock()

    SessionManager._sessions["h"] = {
        "client": old_client,
        "sftp": old_sftp,
        "last_active": 0,
        "lock": MagicMock(),
    }

    new_client = MagicMock()
    new_transport = MagicMock()
    new_transport.is_active.return_value = True
    new_client.get_transport.return_value = new_transport
    new_sftp = MagicMock()
    new_client.open_sftp.return_value = new_sftp
    monkeypatch.setattr("paramiko.SSHClient", lambda: new_client)

    session = SessionManager._ensure_session("h")

    old_sftp.close.assert_called_once()
    old_client.close.assert_called_once()
    assert session["client"] is new_client
    assert session["sftp"] is new_sftp


def test_upload_download(monkeypatch):
    session = {
        "client": MagicMock(),
        "sftp": MagicMock(),
        "last_active": 0,
        "lock": MagicMock(),
    }
    # 让 lock 可作为上下文管理器
    session["lock"].__enter__ = lambda *args: None
    session["lock"].__exit__ = lambda *args: None

    monkeypatch.setattr(
        "alma_linux_remote_plugin.session_manager.SessionManager._ensure_session",
        lambda host_name: session,
    )

    up = SessionManager.upload_file("h", "a", "b")
    down = SessionManager.download_file("h", "b", "a")

    assert "上传成功" in up
    assert "下载成功" in down


def test_run_command_block_dangerous(monkeypatch):
    # 命中危险命令时，不应创建会话
    called = {"ensure": False}

    def fake_ensure(host_name):
        called["ensure"] = True
        return {}

    monkeypatch.setattr(
        "alma_linux_remote_plugin.session_manager.SessionManager._ensure_session",
        fake_ensure,
    )

    result = SessionManager.run_command("h", "rm -rf /")
    assert result.success is False
    assert result.blocked is True
    assert result.reason and result.reason.startswith("blocked_by_pattern")
    assert "危险操作已拦截" in result.stderr
    assert called["ensure"] is False


def test_run_command_batch_collects_results_in_input_order(monkeypatch):
    SessionManager._sessions = {}
    SessionManager._cleanup_thread = None

    def fake_run_command(host_name, command, timeout=60):
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "command": command,
            "exit_code": 0,
            "stdout": f"{host_name}:ok",
            "stderr": "",
            "success": True,
            "blocked": False,
            "reason": None,
            "suggestions": [],
        }
        return mock_result

    monkeypatch.setattr(
        "alma_linux_remote_plugin.session_manager.SessionManager.run_command",
        fake_run_command,
    )

    result = SessionManager.run_command_batch(["h1", "h2", "h1"], "hostname", max_workers=8)

    assert result.total == 2
    assert result.success_count == 2
    assert result.failure_count == 0
    assert [item.host_name for item in result.items] == ["h1", "h2"]
    assert [item.stdout for item in result.items] == ["h1:ok", "h2:ok"]


def test_run_command_batch_captures_exception_per_host(monkeypatch):
    SessionManager._sessions = {}
    SessionManager._cleanup_thread = None

    def fake_run_command(host_name, command, timeout=60):
        if host_name == "bad":
            raise ValueError("主机 bad 未配置")
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "command": command,
            "exit_code": 0,
            "stdout": "ok",
            "stderr": "",
            "success": True,
            "blocked": False,
            "reason": None,
            "suggestions": [],
        }
        return mock_result

    monkeypatch.setattr(
        "alma_linux_remote_plugin.session_manager.SessionManager.run_command",
        fake_run_command,
    )

    result = SessionManager.run_command_batch(["good", "bad"], "uptime")

    assert result.total == 2
    assert result.success_count == 1
    assert result.failure_count == 1
    assert result.items[1].host_name == "bad"
    assert result.items[1].success is False
    assert result.items[1].exit_code == 255
    assert "未配置" in result.items[1].stderr


def test_run_command_batch_preserves_blocked_result(monkeypatch):
    SessionManager._sessions = {}
    SessionManager._cleanup_thread = None

    def fake_run_command(host_name, command, timeout=60):
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "command": command,
            "exit_code": 126,
            "stdout": "",
            "stderr": "危险操作已拦截，请用户自行操作",
            "success": False,
            "blocked": True,
            "reason": "dangerous_operation",
            "suggestions": ["请用户自行 SSH 登录目标主机执行该命令"],
        }
        return mock_result

    monkeypatch.setattr(
        "alma_linux_remote_plugin.session_manager.SessionManager.run_command",
        fake_run_command,
    )

    result = SessionManager.run_command_batch(["h1"], "rm -rf /")

    assert result.total == 1
    assert result.failure_count == 1
    assert result.items[0].blocked is True
    assert result.items[0].reason == "dangerous_operation"


def test_run_command_batch_requires_hosts():
    with pytest.raises(ValueError, match="host_names 不能为空"):
        SessionManager.run_command_batch([], "uptime")


def test_upload_file_batch_collects_results_in_input_order(monkeypatch):
    SessionManager._sessions = {}
    SessionManager._cleanup_thread = None

    monkeypatch.setattr(
        "alma_linux_remote_plugin.session_manager.SessionManager.upload_file",
        lambda host_name, local_path, remote_path: f"上传成功 {local_path} → {remote_path} ({host_name})",
    )

    result = SessionManager.upload_file_batch(["h1", "h2", "h1"], "a.txt", "/tmp/a.txt")

    assert result.total == 2
    assert result.success_count == 2
    assert [item.host_name for item in result.items] == ["h1", "h2"]
    assert result.items[0].local_path == "a.txt"
    assert result.items[0].remote_path == "/tmp/a.txt"


def test_upload_file_batch_captures_exception_per_host(monkeypatch):
    SessionManager._sessions = {}
    SessionManager._cleanup_thread = None

    def fake_upload_file(host_name, local_path, remote_path):
        if host_name == "bad":
            raise RuntimeError("disk full")
        return f"上传成功 {local_path} → {remote_path}"

    monkeypatch.setattr(
        "alma_linux_remote_plugin.session_manager.SessionManager.upload_file",
        fake_upload_file,
    )

    result = SessionManager.upload_file_batch(["good", "bad"], "a.txt", "/tmp/a.txt")

    assert result.total == 2
    assert result.failure_count == 1
    assert result.items[1].host_name == "bad"
    assert result.items[1].success is False
    assert result.items[1].error == "disk full"


def test_download_file_batch_uses_template_and_preserves_order(monkeypatch):
    SessionManager._sessions = {}
    SessionManager._cleanup_thread = None

    monkeypatch.setattr(
        "alma_linux_remote_plugin.session_manager.SessionManager.download_file",
        lambda host_name, remote_path, local_path: f"下载成功 {remote_path} → {local_path}",
    )

    result = SessionManager.download_file_batch(
        ["h1", "h2"],
        "/var/log/app.log",
        "/tmp/{host_name}-{remote_basename}",
    )

    assert result.total == 2
    assert result.success_count == 2
    assert [item.local_path for item in result.items] == [
        "/tmp/h1-app.log",
        "/tmp/h2-app.log",
    ]


def test_download_file_batch_requires_host_name_placeholder():
    with pytest.raises(ValueError, match="local_path_template 必须包含 \\{host_name\\} 占位符"):
        SessionManager.download_file_batch(["h1"], "/var/log/app.log", "/tmp/app.log")
