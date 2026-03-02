# alma-linux-remote-plugin

**专为 Alma AI Agent 设计的原子级无状态 Linux SSH Skill**

一个极简、可靠、无状态的 Linux 远程管理插件，专为 Alma 设计。只保留最纯的原子操作，完美适配 LangGraph、CrewAI、AutoGen 等 AI Agent 框架。

---

## ✨ 特性

- **完全无状态**：每次调用独立 SSH 连接，执行完立即关闭，无 session_id 管理负担
- **原子级操作**：5 个最核心工具，AI 直接 tool-call
- **Alma Skill 原生支持**：严格遵循官方 `manifest.json` + `runtime_adapter.py` 规范
- **安全优先**：密码/密钥均通过环境变量传入，连接用时创建、用完即毁
- **uv 管理**：现代 Python 项目管理，安装极简
- **支持密码 & SSH 密钥** 两种认证方式

---

## 📦 安装

```bash
# 1. 创建项目（如果还没有）
uv init alma-linux-remote-plugin --lib
cd alma-linux-remote-plugin

# 2. 安装依赖
uv sync
uv pip install -e .

⚙️ 配置

复制配置文件Bashcp hosts.yaml.example hosts.yaml
cp .env.example .env
编辑 hosts.yamlYAMLhosts:
  my-server:          # ← 主机别名，AI 会用这个名称调用
    host: 192.168.1.100
    username: root
    auth:
      method: password
      password_env: MY_SERVER_PASS
  dev-box:
    host: dev.example.com
    username: ubuntu
    auth:
      method: key
      key_path: ~/.ssh/id_ed25519
编辑 .envenvMY_SERVER_PASS=你的真实密码


🛠️ 可用工具（Alma 会自动注册）
工具名称描述参数返回值类型list_hosts列出所有可用主机无List[str]test_connection测试连通性host_name, timeout?strrun_command执行单条命令（核心）host_name, command, timeout?CommandResultupload_file上传文件host_name, local_path, remote_pathstr（成功提示）download_file下载文件host_name, remote_path, local_pathstr（成功提示）
run_command 返回示例：
JSON{
  "command": "uptime",
  "exit_code": 0,
  "stdout": " 14:30:01 up 3 days...",
  "stderr": "",
  "success": true
}

🚀 在 Alma 中使用示例
Alma 会自动发现并注册这些工具，你可以直接在对话中让 AI 使用：
textAI：请帮我检查服务器 my-server 的磁盘使用情况
→ Alma 调用 run_command("my-server", "df -h")
textAI：把本地的 deploy.sh 上传到 /opt/app/
→ Alma 调用 upload_file(...)

📁 文件结构
textalma-linux-remote-plugin/
├── manifest.json
├── README.md
├── hosts.yaml.example
├── .env.example
├── pyproject.toml
└── src/
    └── alma_linux_remote_plugin/
        ├── __init__.py
        ├── runtime_adapter.py   # Alma 入口
        ├── tools.py             # 纯函数
        ├── ssh.py
        ├── config.py
        └── models.py

🔒 安全注意事项

密码/密钥只通过环境变量传入，绝不硬编码
每次操作独立连接，无持久会话
生产环境建议使用 SSH 密钥 + AutoAddPolicy 可根据需要改为 RejectPolicy
