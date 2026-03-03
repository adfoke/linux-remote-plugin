---
name: alma-linux-remote-plugin
description: Stateful Linux remote management for Alma/Pi agents via SSH/SFTP. All remote operations use persistent sessions (no stateless mode), with 5-minute idle timeout, SQLite audit logging, and FastAPI dashboard for audit viewing.
allowed-tools:
  - Bash
  - Read
  - Write
---

# Alma Linux Remote Plugin Skill

## Purpose

Use this skill to operate remote Linux hosts safely through the plugin tools:

- `list_hosts`
- `test_connection`
- `run_command`
- `upload_file`
- `download_file`

This project is **stateful-first**:

- `test_connection` now also uses persistent session flow
- if session exists → reuse
- if not → auto-create
- idle timeout defaults to **300 seconds (5 minutes)**

---

## Required Execution Order (Agent Policy)

When handling user requests, follow this order unless user explicitly overrides:

1. `list_hosts` (discover available targets)
2. `test_connection(host_name)` (validate or create session)
3. `run_command(...)` / `upload_file(...)` / `download_file(...)`
4. Summarize outputs and risks clearly

Do **not** assume host aliases that are not in `hosts.yaml`.

---

## Tool Contracts

### 1) list_hosts
- args: `{}`
- returns: `string[]`

### 2) test_connection
- args: `{ "host_name": string, "timeout"?: number }`
- behavior: uses persistent session manager (reuse/create session)
- returns: success/failure message string

### 3) run_command
- args: `{ "host_name": string, "command": string, "timeout"?: number }`
- returns:
  - `command`
  - `exit_code`
  - `stdout`
  - `stderr`
  - `success`

### 4) upload_file
- args: `{ "host_name": string, "local_path": string, "remote_path": string }`
- returns: message string

### 5) download_file
- args: `{ "host_name": string, "remote_path": string, "local_path": string }`
- returns: message string

---

## Session Semantics

- Session key: per `host_name`
- Auto keepalive enabled
- Idle cleanup thread runs periodically
- Cleanup threshold: `session.idle_timeout_seconds` (default 300)

If a command fails due to stale transport, retry once by re-running `test_connection` then re-run command.

---

## Audit & Observability

Audit is stored in SQLite (no JSONL file mode):

- default DB: `./logs/audit.db`
- table: `audit_logs`

FastAPI dashboard:

- `GET /` → web page
- `GET /api/logs` → query API

Supported query parameters:

- `page`
- `page_size`
- `host_name`
- `operation_type`
- `start_time` (ISO8601)
- `end_time` (ISO8601)

When user asks “查看AI操作日志”, prefer directing to dashboard/API filters first.

---

## Safety Rules

- Never echo secrets from `.env` (key passphrase or other secrets)
- Never fabricate command output
- Command policy is configurable:
  - `policy.default_mode = blocklist` (default)
  - `policy.default_mode = strict_allowlist`
  - `policy.host_overrides.<host>` for per-host policy
- If command is blocked, return clear manual steps; do not attempt bypass
- Always show host + command in response summary

---

## Recommended Response Style

For each remote action, report:

1. Target host
2. Command/file action
3. Exit result (success/failure)
4. Key stdout/stderr summary
5. Next suggested step

---

## Examples

### Health check
1. `list_hosts`
2. `test_connection("prod-web-1")`
3. `run_command("prod-web-1", "uptime && df -h")`

### Upload and verify
1. `test_connection("prod-web-1")`
2. `upload_file("prod-web-1", "./deploy.sh", "/tmp/deploy.sh")`
3. `run_command("prod-web-1", "chmod +x /tmp/deploy.sh && /tmp/deploy.sh --check")`

### Audit query (API)
- `/api/logs?page=1&page_size=50&host_name=prod-web-1&start_time=2026-03-03T00:00:00Z&end_time=2026-03-03T23:59:59Z`
