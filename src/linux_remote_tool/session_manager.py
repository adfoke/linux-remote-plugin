from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import threading
import time
from typing import Any, Callable, Dict, TypeVar

import paramiko

from .audit import AuditLogger
from .config import load_config, load_hosts
from .models import (
    BatchCommandItem,
    BatchCommandResult,
    BatchConnectionItem,
    BatchConnectionResult,
    BatchTransferItem,
    BatchTransferResult,
    CommandResult,
    SessionConfig,
)
from .safety import evaluate_command_policy
from .ssh import SSHManager

T = TypeVar("T")


class SessionManager:
    """自动 Lazy Session 管理器。"""

    _sessions: Dict[str, Dict[str, Any]] = {}
    _lock = threading.Lock()
    _cleanup_thread: threading.Thread | None = None

    @classmethod
    def _get_config(cls) -> SessionConfig:
        try:
            return load_config("hosts.yaml").session
        except Exception:
            return SessionConfig(idle_timeout_seconds=300)

    @classmethod
    def _close_session(cls, host_name: str, session: Dict[str, Any], reason: str) -> None:
        try:
            session["sftp"].close()
        except Exception:
            pass

        try:
            session["client"].close()
        except Exception:
            pass

        try:
            AuditLogger().log("session_cleanup", host_name, {"reason": reason})
        except Exception:
            pass

    @classmethod
    def _close_client_resources(cls, client: paramiko.SSHClient, sftp: Any | None = None) -> None:
        if sftp is not None:
            try:
                sftp.close()
            except Exception:
                pass

        try:
            client.close()
        except Exception:
            pass

    @classmethod
    def _ensure_session(cls, host_name: str, timeout: int = 30):
        with cls._lock:
            if host_name in cls._sessions:
                session = cls._sessions[host_name]
                transport = session["client"].get_transport()
                if transport and transport.is_active():
                    session["last_active"] = time.time()
                    return session
                cls._close_session(host_name, session, "inactive_transport")
                cls._sessions.pop(host_name, None)

            hosts = load_hosts()
            if host_name not in hosts:
                raise ValueError(f"主机 {host_name} 未配置")
            host_cfg = hosts[host_name]

        client = paramiko.SSHClient()
        sftp = None
        try:
            SSHManager._connect(client, host_cfg, timeout)
            transport = client.get_transport()
            if transport:
                transport.set_keepalive(30)
            sftp = client.open_sftp()
        except Exception:
            cls._close_client_resources(client, sftp)
            raise

        session_started = False
        with cls._lock:
            existing_session = cls._sessions.get(host_name)
            if existing_session:
                transport = existing_session["client"].get_transport()
                if transport and transport.is_active():
                    existing_session["last_active"] = time.time()
                    cls._close_client_resources(client, sftp)
                    return existing_session
                cls._close_session(host_name, existing_session, "inactive_transport")
                cls._sessions.pop(host_name, None)

            session = {
                "client": client,
                "sftp": sftp,
                "last_active": time.time(),
                "lock": threading.Lock(),
            }
            cls._sessions[host_name] = session
            session_started = True

            if cls._cleanup_thread is None or not cls._cleanup_thread.is_alive():
                cls._cleanup_thread = threading.Thread(target=cls._cleanup_idle, daemon=True)
                cls._cleanup_thread.start()

        if session_started:
            AuditLogger().log("session_auto_start", host_name, {"lazy": True})
        return session

    @classmethod
    def _cleanup_idle(cls):
        while True:
            time.sleep(30)
            with cls._lock:
                now = time.time()
                timeout = cls._get_config().idle_timeout_seconds
                for host, session in list(cls._sessions.items()):
                    if now - session["last_active"] > timeout:
                        cls._close_session(host, session, "idle")
                        cls._sessions.pop(host, None)

    @staticmethod
    def _prepare_batch_hosts(host_names: list[str]) -> list[str]:
        unique_host_names = list(dict.fromkeys(host_names))
        if not unique_host_names:
            raise ValueError("host_names 不能为空")
        return unique_host_names

    @staticmethod
    def _resolve_worker_count(max_workers: int, host_count: int) -> int:
        return max(1, min(max_workers, host_count, 10))

    @classmethod
    def _execute_batch(
        cls,
        host_names: list[str],
        max_workers: int,
        runner: Callable[[str], T],
    ) -> list[T]:
        unique_host_names = cls._prepare_batch_hosts(host_names)
        worker_count = cls._resolve_worker_count(max_workers, len(unique_host_names))
        results_by_host: Dict[str, T] = {}

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(runner, host_name): host_name for host_name in unique_host_names
            }
            for future in as_completed(future_map):
                host_name = future_map[future]
                results_by_host[host_name] = future.result()

        return [results_by_host[host_name] for host_name in unique_host_names]

    @classmethod
    def run_command(cls, host_name: str, command: str, timeout: int = 60) -> CommandResult:
        policy = load_config("hosts.yaml").policy
        allowed, reason, mode = evaluate_command_policy(host_name, command, policy)
        if not allowed:
            suggestions = [
                "请用户自行 SSH 登录目标主机执行该命令",
                "先执行只读检查命令评估影响范围",
            ]
            blocked_result = CommandResult(
                command=command,
                exit_code=126,
                stdout="",
                stderr="危险操作已拦截，请用户自行操作",
                success=False,
                blocked=True,
                reason=reason or "dangerous_operation",
                suggestions=suggestions,
            )
            AuditLogger().log(
                "dangerous_block",
                host_name,
                {
                    "command": command,
                    "policy_mode": mode,
                    "policy_reason": blocked_result.reason,
                    "message": blocked_result.stderr,
                    "success": False,
                    "blocked": True,
                    "session_mode": "persistent",
                },
            )
            return blocked_result

        session = cls._ensure_session(host_name, timeout)
        with session["lock"]:
            start = time.perf_counter()
            client = session["client"]
            try:
                _, stdout, stderr = client.exec_command(command, timeout=timeout)
                out = stdout.read().decode("utf-8", errors="replace").strip()
                err = stderr.read().decode("utf-8", errors="replace").strip()
                exit_code = stdout.channel.recv_exit_status()
                result = CommandResult(
                    command=command,
                    exit_code=exit_code,
                    stdout=out,
                    stderr=err,
                    success=exit_code == 0,
                )

                duration = int((time.perf_counter() - start) * 1000)
                AuditLogger().log(
                    "run_command",
                    host_name,
                    {
                        "command": command,
                        "exit_code": exit_code,
                        "success": result.success,
                        "stdout_summary": out[:300] + ("..." if len(out) > 300 else ""),
                        "duration_ms": duration,
                        "session_mode": "persistent",
                    },
                )
                session["last_active"] = time.time()
                return result
            except Exception as e:
                AuditLogger().log("run_command", host_name, {"error": str(e)})
                raise

    @classmethod
    def test_connection(cls, host_name: str, timeout: int = 15) -> None:
        start = time.perf_counter()
        try:
            session = cls._ensure_session(host_name, timeout)
            session["last_active"] = time.time()
            AuditLogger().log(
                "test_connection",
                host_name,
                {
                    "success": True,
                    "duration_ms": int((time.perf_counter() - start) * 1000),
                    "session_mode": "persistent",
                },
            )
        except Exception as exc:
            AuditLogger().log(
                "test_connection",
                host_name,
                {
                    "success": False,
                    "error": str(exc),
                },
            )
            raise

    @classmethod
    def test_connection_batch(
        cls,
        host_names: list[str],
        timeout: int = 15,
        max_workers: int = 5,
    ) -> BatchConnectionResult:
        unique_host_names = cls._prepare_batch_hosts(host_names)
        worker_count = cls._resolve_worker_count(max_workers, len(unique_host_names))

        def _run_one(host_name: str) -> BatchConnectionItem:
            try:
                cls.test_connection(host_name, timeout)
                return BatchConnectionItem(
                    host_name=host_name,
                    success=True,
                    message=f"{host_name} 连接成功",
                )
            except Exception as exc:
                return BatchConnectionItem(
                    host_name=host_name,
                    success=False,
                    message=f"{host_name} 连接异常: {exc}",
                )

        ordered_items = cls._execute_batch(unique_host_names, worker_count, _run_one)
        success_count = sum(1 for item in ordered_items if item.success)
        batch_result = BatchConnectionResult(
            total=len(ordered_items),
            success_count=success_count,
            failure_count=len(ordered_items) - success_count,
            items=ordered_items,
        )
        AuditLogger().log(
            "test_connection_batch",
            ",".join(unique_host_names),
            {
                "host_count": len(unique_host_names),
                "success_count": batch_result.success_count,
                "failure_count": batch_result.failure_count,
                "max_workers": worker_count,
                "hosts": unique_host_names,
            },
        )
        return batch_result

    @classmethod
    def run_command_batch(
        cls,
        host_names: list[str],
        command: str,
        timeout: int = 60,
        max_workers: int = 5,
    ) -> BatchCommandResult:
        unique_host_names = cls._prepare_batch_hosts(host_names)
        worker_count = cls._resolve_worker_count(max_workers, len(unique_host_names))

        def _run_one(host_name: str) -> BatchCommandItem:
            try:
                result = cls.run_command(host_name, command, timeout)
                return BatchCommandItem(host_name=host_name, **result.model_dump())
            except Exception as exc:
                return BatchCommandItem(
                    host_name=host_name,
                    command=command,
                    exit_code=255,
                    stdout="",
                    stderr=str(exc),
                    success=False,
                    blocked=False,
                    reason=None,
                    suggestions=[],
                )

        ordered_items = cls._execute_batch(unique_host_names, worker_count, _run_one)
        success_count = sum(1 for item in ordered_items if item.success)
        batch_result = BatchCommandResult(
            total=len(ordered_items),
            success_count=success_count,
            failure_count=len(ordered_items) - success_count,
            items=ordered_items,
        )
        AuditLogger().log(
            "run_command_batch",
            ",".join(unique_host_names),
            {
                "command": command,
                "host_count": len(unique_host_names),
                "success_count": batch_result.success_count,
                "failure_count": batch_result.failure_count,
                "max_workers": worker_count,
                "hosts": unique_host_names,
            },
        )
        return batch_result

    @classmethod
    def upload_file_batch(
        cls,
        host_names: list[str],
        local_path: str,
        remote_path: str,
        max_workers: int = 5,
    ) -> BatchTransferResult:
        unique_host_names = cls._prepare_batch_hosts(host_names)
        worker_count = cls._resolve_worker_count(max_workers, len(unique_host_names))

        def _run_one(host_name: str) -> BatchTransferItem:
            try:
                message = cls.upload_file(host_name, local_path, remote_path)
                return BatchTransferItem(
                    host_name=host_name,
                    success=True,
                    message=message,
                    local_path=local_path,
                    remote_path=remote_path,
                )
            except Exception as exc:
                return BatchTransferItem(
                    host_name=host_name,
                    success=False,
                    message=f"上传失败 {local_path} → {remote_path}",
                    local_path=local_path,
                    remote_path=remote_path,
                    error=str(exc),
                )

        ordered_items = cls._execute_batch(unique_host_names, worker_count, _run_one)
        success_count = sum(1 for item in ordered_items if item.success)
        batch_result = BatchTransferResult(
            total=len(ordered_items),
            success_count=success_count,
            failure_count=len(ordered_items) - success_count,
            items=ordered_items,
        )
        AuditLogger().log(
            "upload_file_batch",
            ",".join(unique_host_names),
            {
                "local_path": local_path,
                "remote_path": remote_path,
                "host_count": len(unique_host_names),
                "success_count": batch_result.success_count,
                "failure_count": batch_result.failure_count,
                "max_workers": worker_count,
                "hosts": unique_host_names,
            },
        )
        return batch_result

    @classmethod
    def download_file_batch(
        cls,
        host_names: list[str],
        remote_path: str,
        local_path_template: str,
        max_workers: int = 5,
    ) -> BatchTransferResult:
        if "{host_name}" not in local_path_template:
            raise ValueError("local_path_template 必须包含 {host_name} 占位符")

        unique_host_names = cls._prepare_batch_hosts(host_names)
        worker_count = cls._resolve_worker_count(max_workers, len(unique_host_names))

        def _render_local_path(host_name: str) -> str:
            return local_path_template.format(
                host_name=host_name,
                remote_basename=Path(remote_path).name,
            )

        def _run_one(host_name: str) -> BatchTransferItem:
            local_path = _render_local_path(host_name)
            try:
                message = cls.download_file(host_name, remote_path, local_path)
                return BatchTransferItem(
                    host_name=host_name,
                    success=True,
                    message=message,
                    local_path=local_path,
                    remote_path=remote_path,
                )
            except Exception as exc:
                return BatchTransferItem(
                    host_name=host_name,
                    success=False,
                    message=f"下载失败 {remote_path} → {local_path}",
                    local_path=local_path,
                    remote_path=remote_path,
                    error=str(exc),
                )

        ordered_items = cls._execute_batch(unique_host_names, worker_count, _run_one)
        success_count = sum(1 for item in ordered_items if item.success)
        batch_result = BatchTransferResult(
            total=len(ordered_items),
            success_count=success_count,
            failure_count=len(ordered_items) - success_count,
            items=ordered_items,
        )
        AuditLogger().log(
            "download_file_batch",
            ",".join(unique_host_names),
            {
                "remote_path": remote_path,
                "local_path_template": local_path_template,
                "host_count": len(unique_host_names),
                "success_count": batch_result.success_count,
                "failure_count": batch_result.failure_count,
                "max_workers": worker_count,
                "hosts": unique_host_names,
            },
        )
        return batch_result

    @classmethod
    def upload_file(cls, host_name: str, local_path: str, remote_path: str) -> str:
        session = cls._ensure_session(host_name)
        with session["lock"]:
            session["sftp"].put(local_path, remote_path)
            AuditLogger().log(
                "upload_file",
                host_name,
                {
                    "local_path": local_path,
                    "remote_path": remote_path,
                    "session_mode": "persistent",
                },
            )
            session["last_active"] = time.time()
            return f"上传成功 {local_path} → {remote_path}"

    @classmethod
    def download_file(cls, host_name: str, remote_path: str, local_path: str) -> str:
        session = cls._ensure_session(host_name)
        with session["lock"]:
            session["sftp"].get(remote_path, local_path)
            AuditLogger().log(
                "download_file",
                host_name,
                {
                    "remote_path": remote_path,
                    "local_path": local_path,
                    "session_mode": "persistent",
                },
            )
            session["last_active"] = time.time()
            return f"下载成功 {remote_path} → {local_path}"
