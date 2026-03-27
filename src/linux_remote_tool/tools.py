from __future__ import annotations

from typing import Any, Dict, List

from .audit import AuditLogger
from .config import load_hosts
from .models import (
    BatchCommandResult,
    BatchConnectionResult,
    BatchTransferResult,
    CommandResult,
)
from .session_manager import SessionManager


def list_hosts() -> List[str]:
    """列出所有可用主机。"""
    return list(load_hosts().keys())


def test_connection(host_name: str, timeout: int = 15) -> str:
    """测试连通性（复用/创建持久会话）。"""
    try:
        SessionManager.test_connection(host_name, timeout)
        return f"{host_name} 连接成功"
    except Exception as e:
        return f"{host_name} 连接异常: {e}"


def run_command(host_name: str, command: str, timeout: int = 60) -> CommandResult:
    """执行命令（自动 Lazy Session + 状态保留）。"""
    return SessionManager.run_command(host_name, command, timeout)


def test_connection_batch(
    host_names: List[str],
    timeout: int = 15,
    max_workers: int = 5,
) -> BatchConnectionResult:
    """并发测试多台主机连通性，返回逐台结果。"""
    return SessionManager.test_connection_batch(host_names, timeout, max_workers)


test_connection_batch.__test__ = False


def run_command_batch(
    host_names: List[str],
    command: str,
    timeout: int = 60,
    max_workers: int = 5,
) -> BatchCommandResult:
    """并发在多台主机执行同一命令，返回结构化结果。"""
    return SessionManager.run_command_batch(host_names, command, timeout, max_workers)


def upload_file(host_name: str, local_path: str, remote_path: str) -> str:
    """上传文件（自动 Session）。"""
    return SessionManager.upload_file(host_name, local_path, remote_path)


def upload_file_batch(
    host_names: List[str],
    local_path: str,
    remote_path: str,
    max_workers: int = 5,
) -> BatchTransferResult:
    """并发将同一个本地文件上传到多台主机的同一路径。"""
    return SessionManager.upload_file_batch(host_names, local_path, remote_path, max_workers)


def download_file(host_name: str, remote_path: str, local_path: str) -> str:
    """下载文件（自动 Session）。"""
    return SessionManager.download_file(host_name, remote_path, local_path)


def download_file_batch(
    host_names: List[str],
    remote_path: str,
    local_path_template: str,
    max_workers: int = 5,
) -> BatchTransferResult:
    """并发从多台主机下载同一路径文件到按主机区分的本地路径。"""
    return SessionManager.download_file_batch(
        host_names,
        remote_path,
        local_path_template,
        max_workers,
    )


def query_audit_logs(
    page: int = 1,
    page_size: int = 50,
    limit: int | None = None,
    host_name: str | None = None,
    operation_type: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> Dict[str, Any]:
    """查询 SQLite 审计日志。"""
    return AuditLogger().query_logs(
        page=page,
        page_size=page_size,
        limit=limit,
        host_name=host_name,
        operation_type=operation_type,
        start_time=start_time,
        end_time=end_time,
    )
