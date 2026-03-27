---
name: lr
description: Use lr through the local bridge and CLI to inspect configured hosts, test connections, run commands, transfer files, and query audit logs. Suitable for single-agent and multi-agent workflows in Codex and Pi.
metadata:
  short-description: Use lr remote ops from the local bridge
---

# lr

## Overview

This skill is for Linux remote operations through the local `lr-codex` bridge.
It is also the orchestration layer for single-agent and multi-agent use.

Use it when the user wants to:

- list configured hosts
- test SSH connectivity
- run remote commands
- upload or download files
- inspect audit logs

This skill is intentionally thin. It does not reimplement SSH logic. It calls the existing local bridge and CLI.
Platform wrappers only expose this skill or forward to the shared runtime.

## Prerequisites

- The project dependencies must be installed
- `hosts.yaml` must exist in the project root
- The requested host name must already exist in `hosts.yaml`

## Workflow

1. Start with read-oriented actions:
   - `uv run lr-codex invoke list_hosts`
2. Before the first remote action on a host, prefer:
   - `uv run lr-codex invoke test_connection --args '{"host_name":"my-server"}'`
3. Then run the requested action:
   - `uv run lr-codex invoke run_command --args '{"host_name":"my-server","command":"uname -a"}'`
   - `uv run lr-codex invoke upload_file --args '{"host_name":"my-server","local_path":"./a.txt","remote_path":"/tmp/a.txt"}'`
   - `uv run lr-codex invoke download_file --args '{"host_name":"my-server","remote_path":"/tmp/a.txt","local_path":"./a.txt"}'`
   - `uv run lr-codex invoke query_audit_logs --args '{"limit":10}'`
4. Summarize:
   - host
   - action
   - success or failure
   - key output
   - next step if needed

## Multi-Agent Rules

- Keep orchestration in this skill. Do not move task-splitting logic into platform manifests.
- Prefer batch tools first:
  - `test_connection_batch`
  - `run_command_batch`
  - `upload_file_batch`
  - `download_file_batch`
- Spawn multiple agents only when work is naturally split by host groups or by clearly separate tasks.
- Give each agent a disjoint host set or disjoint local output path.
- All agents must call the same local bridge:
  - `uv run lr-codex invoke ...`
- Do not let agents invent hosts, fake results, or bypass policy checks.
- Do not duplicate SSH, audit, or config handling in skill text or platform wrappers.
- The coordinator agent should merge results into one final summary with per-host outcomes.

## Rules

- Do not invent host names or command results
- If `hosts.yaml` is missing, stop and ask the user to configure it first
- Do not bypass blocked dangerous commands
- Do not expose secrets from `.env`

## Notes

- `lr-codex invoke` returns JSON on stdout
- Failures are returned as JSON on stderr
- The shared runtime stays in `src/linux_remote_tool/runtime_adapter.py`
- This skill works for Pi in skill mode and for Codex through the same bridge
- Platform wrappers are thin shells. They are not the place for multi-agent orchestration
