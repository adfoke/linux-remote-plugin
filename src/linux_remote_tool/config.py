from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

from .models import AuditConfig, HostAuth, HostConfig, RuntimeConfig

load_dotenv()


def _read_yaml(config_path: str = "hosts.yaml") -> Dict[str, Any]:
    path = Path(config_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(
            f"hosts 文件不存在: {path}。请复制 hosts.yaml.example 并重命名为 hosts.yaml"
        )

    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_hosts(config_path: str = "hosts.yaml") -> Dict[str, HostConfig]:
    data = _read_yaml(config_path)
    hosts_raw = data.get("hosts", {})

    hosts: Dict[str, HostConfig] = {}
    for name, cfg in hosts_raw.items():
        cfg_data = dict(cfg or {})
        auth_data = cfg_data.pop("auth", {})
        hosts[name] = HostConfig(**cfg_data, auth=HostAuth(**auth_data))
    return hosts


def load_config(config_path: str = "hosts.yaml") -> RuntimeConfig:
    """Load optional runtime settings. Missing file falls back to defaults."""
    try:
        data = _read_yaml(config_path)
    except FileNotFoundError:
        return RuntimeConfig()

    return RuntimeConfig(
        session=data.get("session", {}),
        audit=data.get("audit", {}),
        policy=data.get("policy", {}),
    )


def load_audit_config(config_path: str = "hosts.yaml") -> AuditConfig:
    return load_config(config_path).audit
