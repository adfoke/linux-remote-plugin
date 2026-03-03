from __future__ import annotations

import re

from .models import PolicyConfig, PolicyHostOverride, PolicyMode


DEFAULT_DANGEROUS_RULES: list[str] = [
    r"\brm\s+-rf\s+/(\s|$)",
    r"\brm\s+-rf\s+\*",
    r"\bdd\b.*\bof=/dev/(sd|vd|nvme|xvd)",
    r"\bmkfs(\.[a-z0-9]+)?\b\s+/dev/",
    r"\b(shutdown|poweroff|halt|reboot)\b",
    r"\biptables\b.*\s-F(\s|$)",
    r"\bfirewall-cmd\b.*--complete-reload",
    r":\(\)\s*\{\s*:\|:\s*&\s*\};:",
    r"\bchmod\s+-R\s+777\s+/(\s|$)",
]


def _compile_patterns(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(p) for p in patterns if p]


def _get_override(policy: PolicyConfig, host_name: str) -> PolicyHostOverride:
    return policy.host_overrides.get(host_name, PolicyHostOverride())


def evaluate_command_policy(
    host_name: str,
    command: str,
    policy: PolicyConfig,
) -> tuple[bool, str | None, PolicyMode]:
    """Return (allowed, reason, mode)."""
    text = (command or "").strip()
    if not text:
        return True, None, policy.default_mode

    if not policy.enabled:
        return True, None, policy.default_mode

    override = _get_override(policy, host_name)
    mode = override.mode or policy.default_mode

    block_patterns = list(policy.block_patterns)
    if override.block_patterns:
        block_patterns.extend(override.block_patterns)
    if not block_patterns:
        block_patterns = list(DEFAULT_DANGEROUS_RULES)

    if mode == "blocklist":
        for pattern in _compile_patterns(block_patterns):
            if pattern.search(text):
                return False, f"blocked_by_pattern:{pattern.pattern}", mode
        return True, None, mode

    # strict_allowlist: 必须命中 allow 模式，且不能命中 block 模式
    allow_patterns = list(policy.allow_patterns)
    if override.allow_patterns:
        allow_patterns = list(override.allow_patterns)

    if not allow_patterns:
        return False, "strict_allowlist_without_rules", mode

    for pattern in _compile_patterns(block_patterns):
        if pattern.search(text):
            return False, f"blocked_by_pattern:{pattern.pattern}", mode

    for pattern in _compile_patterns(allow_patterns):
        if pattern.search(text):
            return True, None, mode

    return False, "not_in_allowlist", mode
