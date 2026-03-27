---
name: lr
description: Use the local lr bridge to inspect configured hosts, test connections, run commands, transfer files, and query audit logs from this repo.
metadata:
  short-description: Use lr remote ops from Codex
---

# lr

## Overview

This plugin exposes the local `lr-codex` bridge. Use it when the user wants SSH-based remote operations against hosts configured in this repo.

## Prerequisites

- The project dependencies must be installed
- `hosts.yaml` must exist in the repo root
- The requested host name must already exist in `hosts.yaml`

## Required Workflow

1. Start with read-oriented actions:
   - `uv run lr-codex tools`
   - `uv run lr-codex invoke list_hosts`
2. Before remote execution on a host, prefer:
   - `uv run lr-codex invoke test_connection --args '{"host_name":"my-server"}'`
3. Then run the requested action with JSON args:
   - `uv run lr-codex invoke run_command --args '{"host_name":"my-server","command":"uname -a"}'`
   - `uv run lr-codex invoke upload_file --args '{"host_name":"my-server","local_path":"./a.txt","remote_path":"/tmp/a.txt"}'`
   - `uv run lr-codex invoke download_file --args '{"host_name":"my-server","remote_path":"/tmp/a.txt","local_path":"./a.txt"}'`
   - `uv run lr-codex invoke query_audit_logs --args '{"limit":10}'`
4. Summarize the host, action, success state, and any failure details.

## Notes

- `lr-codex tools` returns the shared tool schema from `src/linux_remote_plugin/runtime_adapter.py`
- `lr-codex invoke` returns JSON on stdout and errors as JSON on stderr
- Do not invent host names or command results
- If `hosts.yaml` is missing, stop and ask the user to configure it first
