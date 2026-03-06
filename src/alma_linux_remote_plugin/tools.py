from __future__ import annotations

from typing import Any, Dict, List, Optional

from .audit import AuditLogger
from .config import load_hosts
from .models import CommandResult
from .session_manager import SessionManager


def list_hosts() -> List[str]:
    """列出所有可用主机。"""
    return list(load_hosts().keys())


def test_connection(host_name: str, timeout: int = 15) -> str:
    """测试连通性（复用/创建持久会话）。"""
    try:
        result = SessionManager.run_command(host_name, "echo 'connected'", timeout)
        return f"{host_name} 连接成功" if result.success else f"{host_name} 连接失败"
    except Exception as e:
        return f"{host_name} 连接异常: {e}"


def run_command(host_name: str, command: str, timeout: int = 60) -> CommandResult:
    """执行命令（自动 Lazy Session + 状态保留）。"""
    return SessionManager.run_command(host_name, command, timeout)


def upload_file(host_name: str, local_path: str, remote_path: str) -> str:
    """上传文件（自动 Session）。"""
    return SessionManager.upload_file(host_name, local_path, remote_path)


def download_file(host_name: str, remote_path: str, local_path: str) -> str:
    """下载文件（自动 Session）。"""
    return SessionManager.download_file(host_name, remote_path, local_path)


def start_audit_web_server(host: Optional[str] = None, port: Optional[int] = None) -> Dict[str, Any]:
    """手动启动审计日志 Web 服务。默认不启动，按需显式调用。"""
    logger = AuditLogger()
    url = logger.start_dashboard(host=host, port=port)
    return logger.dashboard_status() | {"url": url}


def stop_audit_web_server() -> Dict[str, Any]:
    """手动停止审计日志 Web 服务。"""
    logger = AuditLogger()
    logger.stop_dashboard()
    return logger.dashboard_status()


def get_audit_web_server_status() -> Dict[str, Any]:
    """查询审计日志 Web 服务状态。"""
    return AuditLogger().dashboard_status()
