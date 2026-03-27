from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

from .tools import (
    download_file,
    download_file_batch,
    list_hosts,
    query_audit_logs,
    run_command,
    run_command_batch,
    test_connection,
    test_connection_batch,
    upload_file,
    upload_file_batch,
)

COMMAND_ALIASES = {
    "list_hosts": "list-hosts",
    "test_connection": "test-connection",
    "test_connection_batch": "test-connection-batch",
    "run_command": "run-command",
    "run_command_batch": "run-command-batch",
    "upload_file": "upload-file",
    "upload_file_batch": "upload-file-batch",
    "download_file": "download-file",
    "download_file_batch": "download-file-batch",
    "audit_logs": "audit-logs",
    "query_audit_logs": "audit-logs",
}


def _add_help_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-h",
        "--h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit.",
    )


def _common_parent() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format. Default: json.",
    )
    return parent


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lr",
        add_help=False,
        formatter_class=argparse.RawTextHelpFormatter,
        description=(
            "AI-friendly CLI for lr.\n"
            "Default output is structured JSON. Errors go to stderr with non-zero exit codes."
        ),
        epilog=(
            "Examples:\n"
            "  lr list-hosts\n"
            "  lr test-connection my-server\n"
            "  lr run-command my-server 'uname -a'\n"
            "  lr run-command-batch 'uptime' web-1 web-2\n"
            "  lr audit-logs --limit 20\n"
        ),
    )
    _add_help_flag(parser)
    parser.add_argument("--version", action="version", version="lr 1.0.1")

    common_parent = _common_parent()
    subparsers = parser.add_subparsers(dest="command")

    list_hosts_parser = subparsers.add_parser(
        "list-hosts",
        add_help=False,
        parents=[common_parent],
        help="List configured hosts.",
        description="List configured hosts.",
    )
    _add_help_flag(list_hosts_parser)
    list_hosts_parser.set_defaults(handler=_cmd_list_hosts)

    test_connection_parser = subparsers.add_parser(
        "test-connection",
        add_help=False,
        parents=[common_parent],
        help="Test one host connection.",
        description="Test one host connection.",
    )
    _add_help_flag(test_connection_parser)
    test_connection_parser.add_argument("host_name", help="Configured host name.")
    test_connection_parser.add_argument("--timeout", type=int, default=15, help="SSH timeout in seconds.")
    test_connection_parser.set_defaults(handler=_cmd_test_connection)

    test_connection_batch_parser = subparsers.add_parser(
        "test-connection-batch",
        add_help=False,
        parents=[common_parent],
        help="Test multiple hosts in parallel.",
        description="Test multiple hosts in parallel.",
    )
    _add_help_flag(test_connection_batch_parser)
    test_connection_batch_parser.add_argument("host_names", nargs="+", help="Configured host names.")
    test_connection_batch_parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="SSH timeout in seconds.",
    )
    test_connection_batch_parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Max parallel workers.",
    )
    test_connection_batch_parser.set_defaults(handler=_cmd_test_connection_batch)

    run_command_parser = subparsers.add_parser(
        "run-command",
        add_help=False,
        parents=[common_parent],
        help="Run one command on one host.",
        description="Run one command on one host.",
    )
    _add_help_flag(run_command_parser)
    run_command_parser.add_argument("host_name", help="Configured host name.")
    run_command_parser.add_argument("command_text", help="Shell command to run.")
    run_command_parser.add_argument("--timeout", type=int, default=60, help="Command timeout in seconds.")
    run_command_parser.set_defaults(handler=_cmd_run_command)

    run_command_batch_parser = subparsers.add_parser(
        "run-command-batch",
        add_help=False,
        parents=[common_parent],
        help="Run one command on multiple hosts.",
        description="Run one command on multiple hosts.",
    )
    _add_help_flag(run_command_batch_parser)
    run_command_batch_parser.add_argument("command_text", help="Shell command to run.")
    run_command_batch_parser.add_argument("host_names", nargs="+", help="Configured host names.")
    run_command_batch_parser.add_argument("--timeout", type=int, default=60, help="Command timeout in seconds.")
    run_command_batch_parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Max parallel workers.",
    )
    run_command_batch_parser.set_defaults(handler=_cmd_run_command_batch)

    upload_file_parser = subparsers.add_parser(
        "upload-file",
        add_help=False,
        parents=[common_parent],
        help="Upload one file to one host.",
        description="Upload one file to one host.",
    )
    _add_help_flag(upload_file_parser)
    upload_file_parser.add_argument("host_name", help="Configured host name.")
    upload_file_parser.add_argument("local_path", help="Local file path.")
    upload_file_parser.add_argument("remote_path", help="Remote file path.")
    upload_file_parser.set_defaults(handler=_cmd_upload_file)

    upload_file_batch_parser = subparsers.add_parser(
        "upload-file-batch",
        add_help=False,
        parents=[common_parent],
        help="Upload one file to multiple hosts.",
        description="Upload one file to multiple hosts.",
    )
    _add_help_flag(upload_file_batch_parser)
    upload_file_batch_parser.add_argument("local_path", help="Local file path.")
    upload_file_batch_parser.add_argument("remote_path", help="Remote file path.")
    upload_file_batch_parser.add_argument("host_names", nargs="+", help="Configured host names.")
    upload_file_batch_parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Max parallel workers.",
    )
    upload_file_batch_parser.set_defaults(handler=_cmd_upload_file_batch)

    download_file_parser = subparsers.add_parser(
        "download-file",
        add_help=False,
        parents=[common_parent],
        help="Download one file from one host.",
        description="Download one file from one host.",
    )
    _add_help_flag(download_file_parser)
    download_file_parser.add_argument("host_name", help="Configured host name.")
    download_file_parser.add_argument("remote_path", help="Remote file path.")
    download_file_parser.add_argument("local_path", help="Local file path.")
    download_file_parser.set_defaults(handler=_cmd_download_file)

    download_file_batch_parser = subparsers.add_parser(
        "download-file-batch",
        add_help=False,
        parents=[common_parent],
        help="Download one remote file from multiple hosts.",
        description="Download one remote file from multiple hosts.",
    )
    _add_help_flag(download_file_batch_parser)
    download_file_batch_parser.add_argument("remote_path", help="Remote file path.")
    download_file_batch_parser.add_argument(
        "local_path_template",
        help="Local path template. Must include {host_name}.",
    )
    download_file_batch_parser.add_argument("host_names", nargs="+", help="Configured host names.")
    download_file_batch_parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Max parallel workers.",
    )
    download_file_batch_parser.set_defaults(handler=_cmd_download_file_batch)

    audit_logs_parser = subparsers.add_parser(
        "audit-logs",
        add_help=False,
        parents=[common_parent],
        help="Query audit logs from SQLite.",
        description="Query audit logs from SQLite.",
    )
    _add_help_flag(audit_logs_parser)
    audit_logs_parser.add_argument("--page", type=int, default=1, help="Page number. Default: 1.")
    audit_logs_parser.add_argument(
        "--limit",
        type=int,
        help="Limit returned records for this query.",
    )
    audit_logs_parser.add_argument("--host-name", help="Filter by host name.")
    audit_logs_parser.add_argument("--operation-type", help="Filter by operation type.")
    audit_logs_parser.add_argument("--start-time", help="Filter start time, ISO8601.")
    audit_logs_parser.add_argument("--end-time", help="Filter end time, ISO8601.")
    audit_logs_parser.set_defaults(handler=_cmd_audit_logs)

    return parser


def _serialize(data: Any) -> Any:
    if hasattr(data, "model_dump"):
        return data.model_dump()
    return data


def _print_output(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "text":
        data = payload.get("data")
        if isinstance(data, str):
            print(data)
            return
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return

    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _result(command_name: str, data: Any, output_format: str) -> int:
    payload = {
        "command": command_name,
        "data": _serialize(data),
        "ok": True,
    }
    _print_output(payload, output_format)
    return _exit_code_for_success(data)


def _error(command_name: str, message: str, output_format: str) -> int:
    payload = {
        "command": command_name,
        "error": message,
        "ok": False,
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered, file=sys.stderr)
    return 1


def _exit_code_for_success(data: Any) -> int:
    if isinstance(data, dict):
        if "success" in data:
            return 0 if bool(data["success"]) else max(1, int(data.get("exit_code", 1) or 1))
        if "failure_count" in data:
            return 0 if int(data["failure_count"]) == 0 else 1
    if hasattr(data, "success"):
        return 0 if bool(data.success) else max(1, int(getattr(data, "exit_code", 1) or 1))
    if hasattr(data, "failure_count"):
        return 0 if int(data.failure_count) == 0 else 1
    if isinstance(data, str):
        return 0 if "连接成功" in data or "成功" in data else 1
    return 0


def _cmd_list_hosts(args: argparse.Namespace) -> int:
    return _result("list-hosts", list_hosts(), args.format)


def _cmd_test_connection(args: argparse.Namespace) -> int:
    message = test_connection(args.host_name, args.timeout)
    success = "连接成功" in message
    data = {
        "host_name": args.host_name,
        "message": message,
        "success": success,
        "timeout": args.timeout,
    }
    return _result("test-connection", data, args.format)


def _cmd_test_connection_batch(args: argparse.Namespace) -> int:
    data = test_connection_batch(args.host_names, args.timeout, args.max_workers)
    return _result("test-connection-batch", data, args.format)


def _cmd_run_command(args: argparse.Namespace) -> int:
    data = run_command(args.host_name, args.command_text, args.timeout)
    return _result("run-command", data, args.format)


def _cmd_run_command_batch(args: argparse.Namespace) -> int:
    data = run_command_batch(args.host_names, args.command_text, args.timeout, args.max_workers)
    return _result("run-command-batch", data, args.format)


def _cmd_upload_file(args: argparse.Namespace) -> int:
    message = upload_file(args.host_name, args.local_path, args.remote_path)
    data = {
        "host_name": args.host_name,
        "local_path": args.local_path,
        "message": message,
        "remote_path": args.remote_path,
        "success": True,
    }
    return _result("upload-file", data, args.format)


def _cmd_upload_file_batch(args: argparse.Namespace) -> int:
    data = upload_file_batch(args.host_names, args.local_path, args.remote_path, args.max_workers)
    return _result("upload-file-batch", data, args.format)


def _cmd_download_file(args: argparse.Namespace) -> int:
    message = download_file(args.host_name, args.remote_path, args.local_path)
    data = {
        "host_name": args.host_name,
        "local_path": args.local_path,
        "message": message,
        "remote_path": args.remote_path,
        "success": True,
    }
    return _result("download-file", data, args.format)


def _cmd_download_file_batch(args: argparse.Namespace) -> int:
    data = download_file_batch(
        args.host_names,
        args.remote_path,
        args.local_path_template,
        args.max_workers,
    )
    return _result("download-file-batch", data, args.format)


def _cmd_audit_logs(args: argparse.Namespace) -> int:
    data = query_audit_logs(
        page=args.page,
        limit=args.limit,
        host_name=args.host_name,
        operation_type=args.operation_type,
        start_time=args.start_time,
        end_time=args.end_time,
    )
    return _result("audit-logs", data, args.format)


def main(argv: Sequence[str] | None = None) -> int:
    normalized_argv = list(argv) if argv is not None else list(sys.argv[1:])
    if normalized_argv and not normalized_argv[0].startswith("-"):
        normalized_argv[0] = COMMAND_ALIASES.get(normalized_argv[0], normalized_argv[0])

    parser = _build_parser()
    try:
        args = parser.parse_args(normalized_argv)
    except SystemExit as exc:
        return int(exc.code)

    if not hasattr(args, "handler"):
        parser.print_help()
        return 0

    try:
        return int(args.handler(args))
    except Exception as exc:
        return _error(args.command, str(exc), args.format)
