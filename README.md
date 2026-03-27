# lr

给 AI Agent 用的 Linux 远程操作插件。

支持：
- SSH 连通性检查
- 持久会话执行命令
- 上传文件
- 下载文件
- SQLite 审计日志
- CLI 查询审计日志
- Codex 插件适配
- Alma 插件适配

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
uv run lr --help
uv run lr --h
```

常用命令：

```bash
uv run lr list-hosts
uv run lr test-connection my-server
uv run lr run-command my-server "uname -a"
uv run lr upload-file my-server ./a.txt /tmp/a.txt
uv run lr download-file my-server /tmp/a.txt ./a.txt
uv run lr audit-logs
```

审计日志过滤：

```bash
uv run lr audit-logs --limit 10
uv run lr audit-logs --host-name my-server
uv run lr audit-logs --operation-type run_command
uv run lr audit-logs --start-time 2026-03-03T00:00:00Z --end-time 2026-03-03T23:59:59Z
```

默认输出 JSON。

## Codex

仓库现在带了 Codex 插件清单：

- `.codex-plugin/plugin.json`
- `skills/lr/SKILL.md`

另外补了一个本地桥接入口，方便 Codex 或别的宿主进程直接调用现有运行时：

```bash
uv run lr-codex tools
uv run lr-codex invoke list_hosts
uv run lr-codex invoke run_command --args '{"host_name":"my-server","command":"uname -a"}'
```

`tools` 会返回工具定义 JSON，`invoke` 会返回调用结果 JSON。

Codex 侧目前通过插件 skill 暴露 `lr-codex` 的使用方式。这里先走本地桥接，不硬写 `.app.json` / `.mcp.json` 协议壳，避免伪适配。当前仓库已经具备被 Codex 侧继续接入的稳定入口。

## 多平台插件适配

这个仓库现在把“核心能力”和“平台适配层”拆开了。

核心能力在这些位置：

- `src/linux_remote_plugin/tools.py`
- `src/linux_remote_plugin/session_manager.py`
- `src/linux_remote_plugin/runtime_adapter.py`

其中 `src/linux_remote_plugin/runtime_adapter.py` 是共享运行时入口，负责两件事：

- 返回统一工具定义
- 按工具名分发调用

各平台只做自己的薄适配，不复制 SSH、审计、配置这些业务逻辑。

### Alma

Alma 相关文件放在：

- `.alma-plugin/manifest.json`
- `.alma-plugin/runtime_adapter.py`

说明：

- `.alma-plugin/manifest.json` 是 Alma 插件清单
- `.alma-plugin/runtime_adapter.py` 只做转发，最终还是调用 `src/linux_remote_plugin/runtime_adapter.py`

### Codex

Codex 相关文件放在：

- `.codex-plugin/plugin.json`
- `src/linux_remote_plugin/codex_bridge.py`

说明：

- `.codex-plugin/plugin.json` 是 Codex 插件清单
- `codex_bridge.py` 提供本地桥接命令 `lr-codex`
- `lr-codex tools` 输出工具定义
- `lr-codex invoke` 调用单个工具

### 目录约定

建议后续都按这个规则继续扩展：

- 平台专属清单放到 `.<platform>-plugin/`
- 平台专属薄包装放到该目录，或放到 `src/linux_remote_plugin/` 下单独命名
- 共享工具定义和调用逻辑继续收敛在 `src/linux_remote_plugin/runtime_adapter.py`
- 不要在不同平台重复实现同一套工具

### 新增平台时怎么做

如果后面还要接别的平台，建议只做这几步：

1. 新建平台清单目录，比如 `.<platform>-plugin/`
2. 让平台入口转发到 `src/linux_remote_plugin/runtime_adapter.py`
3. 如果平台需要命令行桥接，再单独加一个像 `lr-codex` 这样的入口
4. 不改现有 SSH、文件传输、审计逻辑

这样改动最小，也最不容易把不同平台适配搞散。

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

- `.alma-plugin/runtime_adapter.py`
- `.alma-plugin/manifest.json`
- `src/linux_remote_plugin/runtime_adapter.py`

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
