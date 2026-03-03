import time
import threading
from typing import Dict
import paramiko
from pathlib import Path
from .config import load_config, load_hosts
from .models import CommandResult
from .audit import AuditLogger  # 下面会新增
from .ssh import SSHManager

class SessionManager:
    """全自动 Lazy Session（AI 专属极简版）"""
    _sessions: Dict[str, dict] = {}  # host_name → {"client": client, "sftp": sftp, "last_active": ts, "lock": Lock}
    _lock = threading.Lock()
    _cleanup_thread = None

    @classmethod
    def _get_config(cls):
        try:
            return load_config("hosts.yaml").data.session
        except:
            from .models import SessionConfig  # 兜底
            return SessionConfig(idle_timeout_seconds=300)

    @classmethod
    def _ensure_session(cls, host_name: str):
        """懒加载：不存在就自动创建"""
        with cls._lock:
            if host_name in cls._sessions:
                s = cls._sessions[host_name]
                if s["client"].get_transport() and s["client"].get_transport().is_active():
                    s["last_active"] = time.time()
                    return s

            hosts = load_hosts()
            if host_name not in hosts:
                raise ValueError(f"主机 {host_name} 未配置")

            client = paramiko.SSHClient()
            SSHManager._connect(client, hosts[host_name])
            client.get_transport().set_keepalive(30)
            sftp = client.open_sftp()

            session = {
                "client": client,
                "sftp": sftp,
                "last_active": time.time(),
                "lock": threading.Lock()
            }
            cls._sessions[host_name] = session

            # 启动清理线程
            if cls._cleanup_thread is None or not cls._cleanup_thread.is_alive():
                cls._cleanup_thread = threading.Thread(target=cls._cleanup_idle, daemon=True)
                cls._cleanup_thread.start()

            AuditLogger().log("session_auto_start", host_name, {"lazy": True})
            return session

    @classmethod
    def _cleanup_idle(cls):
        while True:
            time.sleep(30)
            with cls._lock:
                now = time.time()
                timeout = cls._get_config().idle_timeout_seconds
                for host, s in list(cls._sessions.items()):
                    if now - s["last_active"] > timeout:
                        try:
                            s["sftp"].close()
                            s["client"].close()
                            AuditLogger().log("session_cleanup", host, {"reason": "idle"})
                        except:
                            pass
                        cls._sessions.pop(host, None)

    @classmethod
    def run_command(cls, host_name: str, command: str, timeout: int = 60) -> CommandResult:
        session = cls._ensure_session(host_name)
        with session["lock"]:
            start = time.perf_counter()
            client = session["client"]
            try:
                stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
                out = stdout.read().decode("utf-8", errors="replace").strip()
                err = stderr.read().decode("utf-8", errors="replace").strip()
                exit_code = stdout.channel.recv_exit_status()
                result = CommandResult(command=command, exit_code=exit_code, stdout=out, stderr=err, success=exit_code == 0)

                duration = int((time.perf_counter() - start) * 1000)
                AuditLogger().log("run_command", host_name, {
                    "command": command,
                    "exit_code": exit_code,
                    "success": result.success,
                    "stdout_summary": out[:300] + ("..." if len(out) > 300 else ""),
                    "duration_ms": duration,
                    "session_mode": "persistent"
                })
                session["last_active"] = time.time()
                return result
            except Exception as e:
                AuditLogger().log("run_command", host_name, {"error": str(e)})
                raise

    @classmethod
    def upload_file(cls, host_name: str, local_path: str, remote_path: str) -> str:
        session = cls._ensure_session(host_name)
        with session["lock"]:
            session["sftp"].put(local_path, remote_path)
            AuditLogger().log("upload_file", host_name, {"local_path": local_path, "remote_path": remote_path, "session_mode": "persistent"})
            session["last_active"] = time.time()
            return f"✅ 上传成功 {local_path} → {remote_path}"

    @classmethod
    def download_file(cls, host_name: str, remote_path: str, local_path: str) -> str:
        session = cls._ensure_session(host_name)
        with session["lock"]:
            session["sftp"].get(remote_path, local_path)
            AuditLogger().log("download_file", host_name, {"remote_path": remote_path, "local_path": local_path, "session_mode": "persistent"})
            session["last_active"] = time.time()
            return f"✅ 下载成功 {remote_path} → {local_path}"