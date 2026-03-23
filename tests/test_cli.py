import json

from alma_linux_remote_plugin.cli import main
from alma_linux_remote_plugin.models import BatchCommandItem, BatchCommandResult, CommandResult


def test_cli_root_help_supports_long_and_short_aliases(capsys):
    exit_code = main(["--h"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "AI-friendly CLI" in captured.out
    assert "--h, --help" in captured.out


def test_cli_subcommand_help_supports_help_alias(capsys):
    exit_code = main(["run-command", "--help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Run one command on one host." in captured.out
    assert "--timeout" in captured.out


def test_cli_audit_logs_help(capsys):
    exit_code = main(["audit-logs", "--help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Query audit logs from SQLite." in captured.out
    assert "--latest" in captured.out


def test_cli_accepts_underscore_command_alias(monkeypatch, capsys):
    monkeypatch.setattr("alma_linux_remote_plugin.cli.list_hosts", lambda: ["web-1"])

    exit_code = main(["list_hosts"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["command"] == "list-hosts"


def test_cli_list_hosts_outputs_json(monkeypatch, capsys):
    monkeypatch.setattr("alma_linux_remote_plugin.cli.list_hosts", lambda: ["web-1", "web-2"])

    exit_code = main(["list-hosts"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["data"] == ["web-1", "web-2"]


def test_cli_audit_logs_outputs_json(monkeypatch, capsys):
    monkeypatch.setattr(
        "alma_linux_remote_plugin.cli.query_audit_logs",
        lambda **kwargs: {"page": 1, "page_size": 50, "total": 1, "total_pages": 1, "items": []},
    )

    exit_code = main(["audit-logs"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["command"] == "audit-logs"
    assert payload["data"]["total"] == 1


def test_cli_audit_logs_rejects_page_size_option(capsys):
    exit_code = main(["audit-logs", "--page-size", "20"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "--page-size" in captured.err


def test_cli_audit_logs_passes_latest(monkeypatch, capsys):
    called: dict[str, int | None] = {"latest": None}

    def fake_query_audit_logs(**kwargs):
        called["latest"] = kwargs.get("latest")
        return {"page": 1, "page_size": 3, "total": 3, "total_pages": 1, "items": []}

    monkeypatch.setattr("alma_linux_remote_plugin.cli.query_audit_logs", fake_query_audit_logs)

    exit_code = main(["audit-logs", "--latest", "3"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert called["latest"] == 3
    assert payload["data"]["page_size"] == 3


def test_cli_run_command_returns_remote_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(
        "alma_linux_remote_plugin.cli.run_command",
        lambda host_name, command_text, timeout: CommandResult(
            command=command_text,
            exit_code=7,
            stdout="",
            stderr="bad",
            success=False,
        ),
    )

    exit_code = main(["run-command", "web-1", "false"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 7
    assert payload["data"]["success"] is False


def test_cli_run_command_batch_uses_failure_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(
        "alma_linux_remote_plugin.cli.run_command_batch",
        lambda host_names, command_text, timeout, max_workers: BatchCommandResult(
            total=2,
            success_count=1,
            failure_count=1,
            items=[
                BatchCommandItem(
                    host_name="web-1",
                    command=command_text,
                    exit_code=0,
                    stdout="ok",
                    stderr="",
                    success=True,
                ),
                BatchCommandItem(
                    host_name="web-2",
                    command=command_text,
                    exit_code=1,
                    stdout="",
                    stderr="bad",
                    success=False,
                ),
            ],
        ),
    )

    exit_code = main(["run-command-batch", "uptime", "web-1", "web-2"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert payload["data"]["failure_count"] == 1


def test_cli_reports_errors_to_stderr(monkeypatch, capsys):
    monkeypatch.setattr(
        "alma_linux_remote_plugin.cli.list_hosts",
        lambda: (_ for _ in ()).throw(ValueError("boom")),
    )

    exit_code = main(["list-hosts"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error"] == "boom"
