# linux-remote-tool

CLI 名称仍然是 `lr`。

给 AI Agent 用的 Linux 远程操作运行时。

推荐结构：
- 共享运行时
- skill 编排
- 薄接入壳

支持：
- SSH 连通性检查
- 持久会话执行命令
- 上传文件
- 下载文件
- SQLite 审计日志
- CLI 查询审计日志
- Codex skill 接入
- Alma 薄插件接入
- Pi skill 接入

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

## 架构

这个仓库现在把三层拆开了：

- 运行时：`src/linux_remote_tool/runtime_adapter.py`
- skill 编排：`skills/lr/SKILL.md`
- 平台壳：`.codex-plugin/plugin.json`、`.alma-plugin/manifest.json`、`package.json`

职责：

- 运行时只负责工具定义和调用分发
- skill 负责单 agent / 多 agent 的调用流程、约束和总结方式
- manifest 或 package 只负责宿主接入、发现和权限声明

不要把多 agent 编排写进平台接入壳。

## Codex

Codex 侧保留一个很薄的接入壳：

- `.codex-plugin/plugin.json`
- `skills/lr/SKILL.md`

另外补了一个本地桥接入口，方便 Codex 或别的宿主进程直接调用现有运行时：

```bash
uv run lr-codex tools
uv run lr-codex invoke list_hosts
uv run lr-codex invoke run_command --args '{"host_name":"my-server","command":"uname -a"}'
```

`tools` 返回工具定义 JSON，`invoke` 返回调用结果 JSON。

Codex 侧通过接入壳暴露 skill，真正的调用流程放在 `skills/lr/SKILL.md`。

## Pi

仓库现在支持 Pi 的 skill 模式：

- `package.json`
- `skills/lr/SKILL.md`

说明：

- 不做 Pi extension
- 不重复包装一层 TypeScript 工具注册
- Pi 侧直接通过 skill 调用本地 `lr-codex`
- 多 agent 规则也统一放在 skill
- 远程执行、文件传输、审计逻辑仍然只在 Python 核心里维护

如果要在 Pi 里接这个仓库，推荐用 package/skills 方式安装或加载这个 skill。

## 多 Agent

建议规则：

- 先复用 batch tool，不要一上来拆多个 agent
- 真要拆 agent，就按 host 集合或任务类型切开
- 每个 agent 都走同一个 `lr-codex` bridge
- skill 负责约束和汇总
- 接入壳不保存多 agent 状态，不承载编排逻辑

## 多平台接入

共享能力在这些位置：

- `src/linux_remote_tool/tools.py`
- `src/linux_remote_tool/session_manager.py`
- `src/linux_remote_tool/runtime_adapter.py`

其中 `src/linux_remote_tool/runtime_adapter.py` 是共享运行时入口，负责：

- 返回统一工具定义
- 按工具名分发调用

各平台只做薄适配，不复制 SSH、审计、配置这些业务逻辑。

### Alma

Alma 相关文件放在：

- `.alma-plugin/manifest.json`
- `.alma-plugin/runtime_adapter.py`

说明：

- `.alma-plugin/manifest.json` 是 Alma 接入清单
- `.alma-plugin/runtime_adapter.py` 只做转发
- 不在 Alma 接入壳里写多 agent 编排

### Codex

Codex 相关文件放在：

- `.codex-plugin/plugin.json`
- `src/linux_remote_tool/codex_bridge.py`

说明：

- `.codex-plugin/plugin.json` 是 Codex 的薄接入壳
- `codex_bridge.py` 提供本地桥接命令 `lr-codex`
- `lr-codex tools` 输出工具定义
- `lr-codex invoke` 调用单个工具
- skill 负责单 agent / 多 agent 的使用方式

### Pi

Pi 相关文件放在：

- `package.json`
- `skills/lr/SKILL.md`

说明：

- `package.json` 只暴露 `pi.skills`
- Pi 通过 `skills/lr/SKILL.md` 使用本地桥接
- 执行时不直接重写 SSH 逻辑，统一转发到 `lr-codex`
- 多 agent 也不单独做 extension，继续走 skill

### 目录约定

建议后续都按这个规则继续扩展：

- 平台专属清单放到 `.<platform>-plugin/`
- 平台专属薄包装放到该目录，或放到 `src/linux_remote_tool/` 下单独命名
- 单 agent / 多 agent 的流程统一收在 `skills/`
- Pi 这类 package 型宿主，优先放 `skills/` 和 `package.json`
- 共享工具定义和调用逻辑继续收敛在 `src/linux_remote_tool/runtime_adapter.py`
- 不要在不同平台重复实现同一套工具
- 不要在 manifest 里塞编排逻辑

### 新增平台时怎么做

如果后面还要接别的平台，建议只做这几步：

1. 新建平台清单目录，比如 `.<platform>-plugin/`
2. 让平台入口转发到 `src/linux_remote_tool/runtime_adapter.py`
3. 如果平台需要命令行桥接，再单独加一个像 `lr-codex` 这样的入口
4. 在 `skills/` 里写单 agent / 多 agent 的调用规则
5. 对 Pi 这类 package 宿主，优先用 skill 复用现有 CLI / bridge
6. 不改现有 SSH、文件传输、审计逻辑

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
- `src/linux_remote_tool/runtime_adapter.py`

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
