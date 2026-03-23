from __future__ import annotations

from typing import Any, Dict, List

from .models import BatchCommandResult, BatchConnectionResult, BatchTransferResult, CommandResult
from .tools import (
    download_file,
    download_file_batch,
    list_hosts,
    run_command,
    run_command_batch,
    test_connection,
    test_connection_batch,
    upload_file_batch,
    upload_file,
)


class AlmaRuntimeAdapter:
    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_hosts",
                    "description": "列出所有可用 Linux 主机",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "test_connection",
                    "description": "测试主机连通性（复用或创建持久会话）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "host_name": {"type": "string"},
                            "timeout": {"type": "integer", "default": 15},
                        },
                        "required": ["host_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "test_connection_batch",
                    "description": "并发测试多台主机连通性，返回逐台结果",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "host_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                            },
                            "timeout": {"type": "integer", "default": 15},
                            "max_workers": {"type": "integer", "default": 5},
                        },
                        "required": ["host_names"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": "在持久会话中执行命令",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "host_name": {"type": "string"},
                            "command": {"type": "string"},
                            "timeout": {"type": "integer", "default": 60},
                        },
                        "required": ["host_name", "command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_command_batch",
                    "description": "并发在多台主机执行同一命令，默认部分失败不会中断整体",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "host_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                            },
                            "command": {"type": "string"},
                            "timeout": {"type": "integer", "default": 60},
                            "max_workers": {"type": "integer", "default": 5},
                        },
                        "required": ["host_names", "command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "upload_file",
                    "description": "上传文件到远程主机",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "host_name": {"type": "string"},
                            "local_path": {"type": "string"},
                            "remote_path": {"type": "string"},
                        },
                        "required": ["host_name", "local_path", "remote_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "upload_file_batch",
                    "description": "并发将同一个本地文件上传到多台主机的同一路径",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "host_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                            },
                            "local_path": {"type": "string"},
                            "remote_path": {"type": "string"},
                            "max_workers": {"type": "integer", "default": 5},
                        },
                        "required": ["host_names", "local_path", "remote_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "download_file",
                    "description": "从远程主机下载文件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "host_name": {"type": "string"},
                            "remote_path": {"type": "string"},
                            "local_path": {"type": "string"},
                        },
                        "required": ["host_name", "remote_path", "local_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "download_file_batch",
                    "description": "并发从多台主机下载同一路径文件到按主机区分的本地路径模板",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "host_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                            },
                            "remote_path": {"type": "string"},
                            "local_path_template": {"type": "string"},
                            "max_workers": {"type": "integer", "default": 5},
                        },
                        "required": ["host_names", "remote_path", "local_path_template"],
                    },
                },
            },
        ]

    def invoke(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "list_hosts":
            return list_hosts()
        if tool_name == "test_connection":
            return test_connection(args["host_name"], args.get("timeout", 15))
        if tool_name == "test_connection_batch":
            result: BatchConnectionResult = test_connection_batch(
                args["host_names"],
                args.get("timeout", 15),
                args.get("max_workers", 5),
            )
            return result.model_dump()
        if tool_name == "run_command":
            result: CommandResult = run_command(
                args["host_name"], args["command"], args.get("timeout", 60)
            )
            return result.model_dump()
        if tool_name == "run_command_batch":
            result: BatchCommandResult = run_command_batch(
                args["host_names"],
                args["command"],
                args.get("timeout", 60),
                args.get("max_workers", 5),
            )
            return result.model_dump()
        if tool_name == "upload_file":
            return upload_file(args["host_name"], args["local_path"], args["remote_path"])
        if tool_name == "upload_file_batch":
            result: BatchTransferResult = upload_file_batch(
                args["host_names"],
                args["local_path"],
                args["remote_path"],
                args.get("max_workers", 5),
            )
            return result.model_dump()
        if tool_name == "download_file":
            return download_file(args["host_name"], args["remote_path"], args["local_path"])
        if tool_name == "download_file_batch":
            result: BatchTransferResult = download_file_batch(
                args["host_names"],
                args["remote_path"],
                args["local_path_template"],
                args.get("max_workers", 5),
            )
            return result.model_dump()
        raise ValueError(f"未知工具: {tool_name}")


adapter = AlmaRuntimeAdapter()


def get_tools():
    return adapter.get_tools()


def invoke(tool_name: str, args: Dict[str, Any]):
    return adapter.invoke(tool_name, args)
