from typing import List
from .ssh import SSHManager
from .config import load_hosts
from .models import CommandResult

def list_hosts() -> List[str]:
    """列出所有可用主机（AI 第一个要调用的工具）"""
    return list(load_hosts().keys())

def test_connection(host_name: str, timeout: int = 15) -> str:
    """测试连通性"""
    try:
        result = SSHManager.run_command(host_name, "echo '✅ connected'", timeout)
        return f"{host_name} 连接成功" if result.success else f"{host_name} 连接失败"
    except Exception as e:
        return f"{host_name} 连接异常: {e}"

def run_command(host_name: str, command: str, timeout: int = 60) -> CommandResult:
    """最核心原子操作：执行单条命令"""
    return SSHManager.run_command(host_name, command, timeout)

def run_commands(host_name: str, commands: List[str], timeout: int = 60) -> List[CommandResult]:
    """批量执行（AI 自己串联多步）"""
    return [run_command(host_name, cmd, timeout) for cmd in commands]

def upload_file(host_name: str, local_path: str, remote_path: str) -> str:
    """原子上传"""
    SSHManager.upload_file(host_name, local_path, remote_path)
    return f"上传成功 {local_path} → {remote_path} @ {host_name}"

def download_file(host_name: str, remote_path: str, local_path: str) -> str:
    """原子下载"""
    SSHManager.download_file(host_name, remote_path, local_path)
    return f"下载成功 {remote_path} → {local_path} @ {host_name}"