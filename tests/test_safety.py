from linux_remote_tool.models import PolicyConfig, PolicyHostOverride
from linux_remote_tool.safety import evaluate_command_policy


def test_blocklist_mode_blocks_dangerous():
    policy = PolicyConfig(default_mode="blocklist")
    allowed, reason, mode = evaluate_command_policy("h", "rm -rf /", policy)
    assert allowed is False
    assert reason and reason.startswith("blocked_by_pattern")
    assert mode == "blocklist"


def test_blocklist_mode_allows_safe():
    policy = PolicyConfig(default_mode="blocklist")
    allowed, reason, mode = evaluate_command_policy("h", "ls -la /tmp", policy)
    assert allowed is True
    assert reason is None
    assert mode == "blocklist"


def test_strict_allowlist_mode():
    policy = PolicyConfig(
        default_mode="strict_allowlist",
        allow_patterns=[r"^ls(\s|$)", r"^cat\s+/etc/"],
    )
    allowed_ls, _, _ = evaluate_command_policy("h", "ls -la", policy)
    allowed_rm, reason_rm, _ = evaluate_command_policy("h", "rm -rf /tmp/x", policy)
    assert allowed_ls is True
    assert allowed_rm is False
    assert reason_rm == "not_in_allowlist" or reason_rm.startswith("blocked_by_pattern")


def test_host_override_mode_and_allowlist():
    policy = PolicyConfig(
        default_mode="blocklist",
        host_overrides={
            "prod": PolicyHostOverride(
                mode="strict_allowlist",
                allow_patterns=[r"^systemctl\s+status\s+nginx$"],
            )
        },
    )
    ok, _, mode = evaluate_command_policy("prod", "systemctl status nginx", policy)
    bad, reason, _ = evaluate_command_policy("prod", "uname -a", policy)
    assert ok is True
    assert bad is False
    assert reason == "not_in_allowlist"
    assert mode == "strict_allowlist"
