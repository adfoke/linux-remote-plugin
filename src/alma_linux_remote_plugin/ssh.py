from __future__ import annotations

import os

import paramiko

from .config import load_hosts
from .models import CommandResult, HostConfig


class SSHManager:
    """完全无状态：每次调用独立连接，执行完立即关闭。"""

    @staticmethod
    def _connect(client: paramiko.SSHClient, host_cfg: HostConfig, timeout: int = 30):
        kwargs = {
            "hostname": host_cfg.host,
            "port": host_cfg.port,
            "username": host_cfg.username,
            "timeout": timeout,
            "banner_timeout": timeout,
        }
        auth = host_cfg.auth
        if not auth.key_path:
            raise ValueError("key 模式必须配置 key_path")
        kwargs["key_filename"] = os.path.expanduser(auth.key_path)
        if auth.passphrase_env:
            passphrase = os.getenv(auth.passphrase_env)
            if not passphrase:
                raise ValueError(f"环境变量 {auth.passphrase_env} 未设置")
            kwargs["passphrase"] = passphrase

        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        client.connect(**kwargs)

    @staticmethod
    def run_command(host_name: str, command: str, timeout: int = 60) -> CommandResult:
        hosts = load_hosts()
        if host_name not in hosts:
            raise ValueError(f"主机 {host_name} 未配置")
        host_cfg = hosts[host_name]

        client = paramiko.SSHClient()
        try:
            SSHManager._connect(client, host_cfg, timeout)
            _, stdout, stderr = client.exec_command(command, timeout=timeout)
            out = stdout.read().decode("utf-8", errors="replace").strip()
            err = stderr.read().decode("utf-8", errors="replace").strip()
            exit_code = stdout.channel.recv_exit_status()
            return CommandResult(
                command=command,
                exit_code=exit_code,
                stdout=out,
                stderr=err,
                success=exit_code == 0,
            )
        finally:
            client.close()

    @staticmethod
    def upload_file(host_name: str, local_path: str, remote_path: str, timeout: int = 30):
        hosts = load_hosts()
        if host_name not in hosts:
            raise ValueError(f"主机 {host_name} 未配置")
        host_cfg = hosts[host_name]
        client = paramiko.SSHClient()
        try:
            SSHManager._connect(client, host_cfg, timeout)
            with client.open_sftp() as sftp:
                sftp.put(local_path, remote_path)
        finally:
            client.close()

    @staticmethod
    def download_file(host_name: str, remote_path: str, local_path: str, timeout: int = 30):
        hosts = load_hosts()
        if host_name not in hosts:
            raise ValueError(f"主机 {host_name} 未配置")
        host_cfg = hosts[host_name]
        client = paramiko.SSHClient()
        try:
            SSHManager._connect(client, host_cfg, timeout)
            with client.open_sftp() as sftp:
                sftp.get(remote_path, local_path)
        finally:
            client.close()
