import json

from linux_remote_plugin.codex_bridge import main


def test_codex_bridge_tools_outputs_json(capsys):
    exit_code = main(["tools"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["ok"] is True
    assert len(payload["tools"]) == 10


def test_codex_bridge_invoke_uses_inline_json(monkeypatch, capsys):
    monkeypatch.setattr(
        "linux_remote_plugin.codex_bridge.adapter.invoke",
        lambda tool_name, args: {"tool_name": tool_name, "args": args},
    )

    exit_code = main(["invoke", "run_command", "--args", '{"host_name":"web-1","command":"uptime"}'])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["tool"] == "run_command"
    assert payload["result"]["args"]["host_name"] == "web-1"


def test_codex_bridge_rejects_non_object_args(capsys):
    exit_code = main(["invoke", "list_hosts", "--args", '["bad"]'])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error"] == "Tool args must be a JSON object."


def test_codex_bridge_reports_tool_errors(monkeypatch, capsys):
    def raise_exc(tool_name, args):
        raise ValueError(f"bad tool: {tool_name}")

    monkeypatch.setattr("linux_remote_plugin.codex_bridge.adapter.invoke", raise_exc)

    exit_code = main(["invoke", "unknown"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert exit_code == 1
    assert payload["error"] == "bad tool: unknown"
