from unittest.mock import MagicMock, patch

import pytest

from alma_linux_remote_plugin.models import HostAuth, HostConfig
from alma_linux_remote_plugin.ssh import SSHManager


@patch("alma_linux_remote_plugin.ssh.load_hosts")
@patch("paramiko.SSHClient")
def test_run_command_success(mock_ssh_client, mock_load_hosts, monkeypatch):
    monkeypatch.setenv("MY_SERVER_KEY_PASS", "key_pass")
    host_config = HostConfig(
        host="127.0.0.1",
        username="testuser",
        auth=HostAuth(method="key", key_path="~/.ssh/id_ed25519", passphrase_env="MY_SERVER_KEY_PASS"),
    )
    mock_load_hosts.return_value = {"test-server": host_config}

    mock_client = MagicMock()
    mock_ssh_client.return_value = mock_client

    mock_stdout = MagicMock()
    mock_stdout.read.return_value = b"14:30 up 3 days"
    mock_stdout.channel.recv_exit_status.return_value = 0
    mock_stderr = MagicMock()
    mock_stderr.read.return_value = b""
    mock_client.exec_command.return_value = (None, mock_stdout, mock_stderr)

    result = SSHManager.run_command("test-server", "uptime", timeout=10)

    assert result.success is True
    assert "14:30 up" in result.stdout
    mock_client.close.assert_called_once()


@patch("alma_linux_remote_plugin.ssh.load_hosts")
@patch("paramiko.SSHClient")
def test_upload_file(mock_ssh_client, mock_load_hosts):
    host_config = HostConfig(
        host="127.0.0.1",
        username="testuser",
        auth=HostAuth(method="key", key_path="~/.ssh/id_ed25519"),
    )
    mock_load_hosts.return_value = {"test-server": host_config}

    mock_client = MagicMock()
    mock_ssh_client.return_value = mock_client
    mock_sftp = MagicMock()
    mock_client.open_sftp.return_value.__enter__.return_value = mock_sftp

    SSHManager.upload_file("test-server", "/local/file.sh", "/remote/file.sh")

    mock_sftp.put.assert_called_once_with("/local/file.sh", "/remote/file.sh")
    mock_client.close.assert_called_once()


@patch("alma_linux_remote_plugin.ssh.load_hosts")
def test_run_command_host_not_found(mock_load_hosts):
    mock_load_hosts.return_value = {}
    with pytest.raises(ValueError, match="未配置"):
        SSHManager.run_command("missing", "uptime")


@patch("paramiko.SSHClient")
def test_connect_key_passphrase_env_missing(mock_ssh_client):
    host_config = HostConfig(
        host="127.0.0.1",
        username="testuser",
        auth=HostAuth(method="key", key_path="~/.ssh/id_ed25519", passphrase_env="MISSING_ENV"),
    )

    with pytest.raises(ValueError, match="环境变量 MISSING_ENV 未设置"):
        SSHManager._connect(mock_ssh_client.return_value, host_config)
