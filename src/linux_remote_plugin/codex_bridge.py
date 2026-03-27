from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

from .runtime_adapter import adapter


def _parse_args_payload(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Tool args must be a JSON object.")
    return payload


def _load_invoke_args(raw_args: str | None) -> dict[str, Any]:
    if raw_args is not None:
        return _parse_args_payload(raw_args)
    if sys.stdin.isatty():
        return {}
    try:
        stdin_payload = sys.stdin.read().strip()
    except OSError:
        return {}
    if not stdin_payload:
        return {}
    return _parse_args_payload(stdin_payload)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lr-codex",
        description="Codex bridge for lr.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("tools", help="Print tool definitions as JSON.")

    invoke_parser = subparsers.add_parser("invoke", help="Invoke one tool with JSON args.")
    invoke_parser.add_argument("tool_name", help="Tool name from the runtime adapter.")
    invoke_parser.add_argument(
        "--args",
        help="JSON object with tool arguments. If omitted, reads JSON from stdin.",
    )
    return parser


def _write_json(stream: Any, payload: dict[str, Any]) -> None:
    json.dump(payload, stream, ensure_ascii=False)
    stream.write("\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.command == "tools":
            _write_json(sys.stdout, {"ok": True, "tools": adapter.get_tools()})
            return 0

        invoke_args = _load_invoke_args(args.args)
        result = adapter.invoke(args.tool_name, invoke_args)
        _write_json(
            sys.stdout,
            {
                "ok": True,
                "tool": args.tool_name,
                "result": result,
            },
        )
        return 0
    except Exception as exc:
        _write_json(sys.stderr, {"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
