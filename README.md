# alma-linux-remote-plugin

给 Alma Agent 用的 Linux 远程操作插件。

支持：
- SSH 连通性检查
- 持久会话执行命令
- 上传文件
- 下载文件
- SQLite 审计日志
- CLI 查询审计日志

## 安装

```bash
uv sync --group dev
```

或：

```bash
pip install -e .[dev]
```

## 配置

先准备环境变量：

```bash
cp .env.example .env
```

`.env` 只在私钥有口令时需要：

```env
MY_SERVER_KEY_PASS=your_key_passphrase
```

再准备主机配置：

```bash
cp hosts.yaml.example hosts.yaml
```

最小配置：

```yaml
hosts:
  my-server:
    host: 192.168.1.100
    username: root
    auth:
      method: key
      key_path: ~/.ssh/id_ed25519
      passphrase_env: MY_SERVER_KEY_PASS

session:
  idle_timeout_seconds: 300

audit:
  enabled: true
  db_path: ./logs/audit.db

policy:
  enabled: true
  default_mode: blocklist
```

## CLI

看帮助：

```bash
uv run alma-linux-remote --help
uv run alma-linux-remote --h
```

常用命令：

```bash
uv run alma-linux-remote list-hosts
uv run alma-linux-remote test-connection my-server
uv run alma-linux-remote run-command my-server "uname -a"
uv run alma-linux-remote upload-file my-server ./a.txt /tmp/a.txt
uv run alma-linux-remote download-file my-server /tmp/a.txt ./a.txt
uv run alma-linux-remote audit-logs
```

审计日志过滤：

```bash
uv run alma-linux-remote audit-logs --latest 10
uv run alma-linux-remote audit-logs --host-name my-server
uv run alma-linux-remote audit-logs --operation-type run_command
uv run alma-linux-remote audit-logs --start-time 2026-03-03T00:00:00Z --end-time 2026-03-03T23:59:59Z
```

默认输出 JSON。

## Runtime Tools

可用工具：

- `list_hosts()`
- `test_connection(host_name, timeout=15)`
- `test_connection_batch(host_names, timeout=15, max_workers=5)`
- `run_command(host_name, command, timeout=60)`
- `run_command_batch(host_names, command, timeout=60, max_workers=5)`
- `upload_file(host_name, local_path, remote_path)`
- `upload_file_batch(host_names, local_path, remote_path, max_workers=5)`
- `download_file(host_name, remote_path, local_path)`
- `download_file_batch(host_names, remote_path, local_path_template, max_workers=5)`

入口：

- `src/alma_linux_remote_plugin/runtime_adapter.py`
- `manifest.json`

## 规则

- 只支持 key 登录
- 主机 key 必须已在本机 `known_hosts` 中
- 默认复用持久会话
- 空闲超时默认 300 秒
- 危险命令会被拦截
- 审计日志写入 `./logs/audit.db`

## 测试

```bash
uv run --group dev python -m pytest
```
