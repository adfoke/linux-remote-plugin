# alma-linux-remote-plugin

> 专为 Alma AI Agent 设计的 Linux 远程运维插件（SSH/SFTP，持久会话版）

`alma-linux-remote-plugin` 提供一组可被 Agent 调用的工具，用于：

- 列出主机
- 测试 SSH 连通性
- 在远程主机执行命令
- 上传文件到远程主机
- 从远程主机下载文件

项目基于 `paramiko`，并支持**懒加载持久会话**（`test_connection/run_command/upload_file/download_file` 全部走 `SessionManager`）。

---

## 功能特性

- ✅ 持久会话连通性测试（`test_connection`，有会话复用，无会话自动创建）
- ✅ 持久会话命令执行（`run_command`）
- ✅ 危险命令自动拦截（不打断对话流，不执行高危命令）
- ✅ 支持命令策略配置（blocklist / strict_allowlist，支持按主机覆盖）
- ✅ SFTP 上传/下载（`upload_file` / `download_file`）
- ✅ YAML 主机配置加载（`hosts.yaml`）
- ✅ 仅支持 SSH 密钥认证（可选密钥口令来自 `.env`）
- ✅ SQLite 审计日志（默认 `./logs/audit.db`）

---

## 安装

推荐使用 `uv`：

```bash
uv sync --all-extras
```

或用 pip：

```bash
pip install -e .[dev]
```

---

## 配置

### 1) 环境变量

复制并编辑：

```bash
cp .env.example .env
```

`.env.example` 示例：

```env
MY_SERVER_KEY_PASS=your_key_passphrase
```

> 仅在私钥设置口令时需要；`passphrase_env` 会读取这个环境变量。

### 2) 主机配置

复制模板：

```bash
cp hosts.yaml.example hosts.yaml
```

`hosts.yaml.example` 当前内容：

```yaml
hosts:
  my-server:
    host: 192.168.1.100
    username: root
    auth:
      method: key
      key_path: ~/.ssh/id_ed25519
      passphrase_env: MY_SERVER_KEY_PASS
  dev-box:
    host: dev.example.com
    username: ubuntu
    auth:
      method: key
      key_path: ~/.ssh/id_ed25519
```

你也可以加上可选配置：

```yaml
session:
  idle_timeout_seconds: 300

audit:
  enabled: true
  db_path: ./logs/audit.db
  dashboard_host: 127.0.0.1
  dashboard_port: 8765

policy:
  enabled: true
  default_mode: blocklist # blocklist | strict_allowlist

  # blocklist 模式：命中即拦截；为空则使用内置高危规则
  block_patterns:
    - "\\brm\\s+-rf\\s+/(\\s|$)"

  # strict_allowlist 模式：仅允许命中以下规则
  allow_patterns:
    - "^ls(\\s|$)"
    - "^cat\\s+/etc/"

  # 按主机覆盖策略
  host_overrides:
    prod-box:
      mode: strict_allowlist
      allow_patterns:
        - "^systemctl\\s+status\\s+nginx$"
```


---

## 审计日志后台页面

已改为数据库模式，不再写 `audit.jsonl` 文件。

默认配置：

- `db_path = ./logs/audit.db`
- `dashboard_host = 127.0.0.1`
- `dashboard_port = 8765`

你可以在运行时启动日志后台页面（FastAPI + Uvicorn）：

```python
from alma_linux_remote_plugin.audit import AuditLogger

url = AuditLogger().start_dashboard()
print(url)  # 例如 http://127.0.0.1:8765
```

可用接口：

- `GET /`：日志页面
- `GET /api/logs?page=1&page_size=50&host_name=xxx&operation_type=yyy&start_time=2026-03-03T00:00:00Z&end_time=2026-03-03T23:59:59Z`

危险命令拦截会以 `operation_type = dangerous_block` 写入审计库，便于追踪。
在审计详情中可看到 `policy_mode` 与 `policy_reason`。

说明：

- 支持分页：`page`、`page_size`
- 支持时间范围过滤（ISO8601）：`start_time`、`end_time`

---

## 工具列表（Runtime Adapter）

- `list_hosts()`
- `test_connection(host_name, timeout=15)`
- `run_command(host_name, command, timeout=60)`
- `upload_file(host_name, local_path, remote_path)`
- `download_file(host_name, remote_path, local_path)`

对应入口：

- `src/alma_linux_remote_plugin/runtime_adapter.py`
- `manifest.json`（插件元信息）

---

## Python 快速调用示例

```python
from alma_linux_remote_plugin.runtime_adapter import invoke

# 列出主机
print(invoke("list_hosts", {}))

# 测试连接
print(invoke("test_connection", {"host_name": "my-server"}))

# 执行命令
res = invoke("run_command", {
    "host_name": "my-server",
    "command": "uname -a"
})
print(res)
```

---

## 开发与测试

运行测试：

```bash
uv run pytest -q
```

代码检查：

```bash
uv run ruff check src tests
```

---

## 常见问题

### `hosts 文件不存在`

请确认当前工作目录下存在 `hosts.yaml`，并且文件名正确。

### `环境变量 XXX 未设置`

如果你在 `hosts.yaml` 里配置了 `passphrase_env`，请确认 `.env` 中存在该变量，或在系统环境变量中导出。

---

## 许可证

MIT License，见 [LICENSE](./LICENSE)。
