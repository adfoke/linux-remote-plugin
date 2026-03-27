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


class BatchCommandItem(CommandResult):
    host_name: str


class BatchCommandResult(BaseModel):
    total: int
    success_count: int
    failure_count: int
    items: list[BatchCommandItem] = Field(default_factory=list)


class BatchConnectionItem(BaseModel):
    host_name: str
    success: bool
    message: str
    blocked: bool = False
    reason: Optional[str] = None


class BatchConnectionResult(BaseModel):
    total: int
    success_count: int
    failure_count: int
    items: list[BatchConnectionItem] = Field(default_factory=list)


class BatchTransferItem(BaseModel):
    host_name: str
    success: bool
    message: str
    local_path: str
    remote_path: str
    error: Optional[str] = None


class BatchTransferResult(BaseModel):
    total: int
    success_count: int
    failure_count: int
    items: list[BatchTransferItem] = Field(default_factory=list)


class SessionConfig(BaseModel):
    idle_timeout_seconds: int = 300


class AuditConfig(BaseModel):
    enabled: bool = True
    db_path: str = "./logs/audit.db"


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
