from linux_remote_plugin.models import (
    AuditConfig,
    CommandResult,
    HostAuth,
    HostConfig,
    PluginConfig,
    SessionConfig,
)


def test_host_auth_model():
    auth = HostAuth(method="key", key_path="~/.ssh/id_ed25519", passphrase_env="PASS")
    assert auth.method == "key"
    assert auth.key_path == "~/.ssh/id_ed25519"
    assert auth.passphrase_env == "PASS"


def test_host_config_model():
    cfg = HostConfig(
        host="127.0.0.1",
        username="root",
        auth=HostAuth(method="key", key_path="~/.ssh/id_ed25519"),
    )
    assert cfg.port == 22
    assert cfg.host == "127.0.0.1"


def test_command_result():
    result = CommandResult(
        command="uptime",
        exit_code=0,
        stdout="14:30 up ...",
        stderr="",
        success=True,
    )
    assert result.success is True
    assert result.model_dump()["success"] is True


def test_plugin_config_defaults():
    cfg = PluginConfig()
    assert isinstance(cfg.session, SessionConfig)
    assert isinstance(cfg.audit, AuditConfig)
