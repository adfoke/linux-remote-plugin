from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class HostAuth(BaseModel):
    method: Literal["key"] = "key"
    key_path: str
    passphrase_env: Optional[str] = None


class HostConfig(BaseModel):
    host: str
    port: int = 22
    username: str
    auth: HostAuth


class CommandResult(BaseModel):
    command: str
    exit_code: int
    stdout: str
    stderr: str
    success: bool
    blocked: bool = False
    reason: Optional[str] = None
    suggestions: list[str] = Field(default_factory=list)


class SessionConfig(BaseModel):
    idle_timeout_seconds: int = 300


class AuditConfig(BaseModel):
    enabled: bool = True
    db_path: str = "./logs/audit.db"
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8765


PolicyMode = Literal["blocklist", "strict_allowlist"]


class PolicyHostOverride(BaseModel):
    mode: Optional[PolicyMode] = None
    block_patterns: list[str] = Field(default_factory=list)
    allow_patterns: list[str] = Field(default_factory=list)


class PolicyConfig(BaseModel):
    enabled: bool = True
    default_mode: PolicyMode = "blocklist"
    block_patterns: list[str] = Field(default_factory=list)
    allow_patterns: list[str] = Field(default_factory=list)
    host_overrides: dict[str, PolicyHostOverride] = Field(default_factory=dict)


class PluginConfig(BaseModel):
    session: SessionConfig = Field(default_factory=SessionConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
