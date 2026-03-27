import pytest

from linux_remote_tool.config import load_config, load_hosts


def test_load_hosts_success():
    hosts = load_hosts()
    assert "test-server" in hosts
    assert hosts["test-server"].host == "127.0.0.1"
    assert hosts["test-server"].auth.method == "key"


def test_load_hosts_file_not_found():
    with pytest.raises(FileNotFoundError, match="hosts 文件不存在"):
        load_hosts(config_path="/non/existent/hosts.yaml")


def test_load_config_has_defaults():
    cfg = load_config()
    assert cfg.session.idle_timeout_seconds == 300
    assert cfg.audit.enabled is True
    assert cfg.policy.enabled is True
    assert cfg.policy.default_mode == "blocklist"
