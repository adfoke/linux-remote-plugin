---
name: alma-linux-remote-plugin
description: SSH/SFTP remote ops for Alma agents with persistent sessions, command blocking, and SQLite audit logs.
allowed-tools:
  - Bash
  - Read
  - Write
---

# Alma Linux Remote Plugin Skill

## 作用

这个插件用于：

- 查主机
- 建立或复用 SSH 会话
- 执行命令
- 上传文件
- 下载文件
- 查审计日志

## 先后顺序

默认按这个顺序：

1. `list_hosts`
2. `test_connection(host_name)`
3. `run_command` / `upload_file` / `download_file`
4. 总结结果和风险

不要猜主机名。只用 `hosts.yaml` 里已有的名字。

## 工具

- `list_hosts()`
- `test_connection(host_name, timeout=15)`
- `run_command(host_name, command, timeout=60)`
- `upload_file(host_name, local_path, remote_path)`
- `download_file(host_name, remote_path, local_path)`

批量工具也可用：

- `test_connection_batch`
- `run_command_batch`
- `upload_file_batch`
- `download_file_batch`

## 会话规则

- 每台主机一个 session
- 有 session 就复用
- 没有就自动创建
- 默认空闲 300 秒清理

如果命令因为连接失效失败，先重新 `test_connection`，再重试一次。

## 审计日志

日志在 SQLite：

- DB: `./logs/audit.db`
- table: `audit_logs`

查日志走 CLI：

```bash
alma-linux-remote audit-logs --page-size 50
alma-linux-remote audit-logs --host-name prod-web-1
alma-linux-remote audit-logs --operation-type run_command
```

支持过滤：

- `page`
- `page_size`
- `host_name`
- `operation_type`
- `start_time`
- `end_time`

## 安全

- 不要输出 `.env` 里的密钥口令
- 不要编造命令结果
- 命令策略默认是 `blocklist`
- 被拦截的命令不要绕过
- 返回结果时带上主机名和命令

## 响应格式

每次操作至少写清楚：

1. 主机
2. 动作
3. 是否成功
4. 关键输出
5. 下一步
