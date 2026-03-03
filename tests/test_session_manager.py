from unittest.mock import MagicMock

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
