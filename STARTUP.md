# NanoBot 项目启动手册

## 项目概述

NanoBot 是一个轻量级的 **AI 助手框架**，支持：
- 多渠道接入（飞书、钉钉、Telegram、Discord、WhatsApp 等）
- 工具调用（网页搜索、浏览器自动化、天气查询、定时任务等）
- 知识库检索
- Web UI 管理界面

---

## 一、环境准备

### 1. Python 环境要求

| 操作系统 | 要求 |
|---------|------|
| **Windows** | Python 3.11+, 建议使用 Python 3.12 |
| **macOS** | Python 3.11+ |
| **Linux** | Python 3.11+, 推荐 Ubuntu 20.04+ |

```bash
# 验证 Python 版本
python --version
```

### 2. 系统依赖

| 操作系统 | 需要安装的系统包 |
|---------|----------------|
| **Windows** | 无特殊要求 |
| **macOS** | `Command Line Tools`: `xcode-select --install` |
| **Linux (Ubuntu/Debian)** | `sudo apt-get install -y build-essential libgbm-dev libasound2-dev` |
| **Linux (CentOS/RHEL)** | `sudo yum install -y gcc glibc libstdc++` |

---

## 二、获取代码

### 方式一：从 GitHub 克隆（推荐开发使用）

```bash
# Windows / macOS / Linux
git clone https://github.com/your-repo/nanobot.git
cd nanobot
```

### 方式二：直接下载 release 包

```bash
# 使用 curl 或 wget
curl -L -o nanobot.zip https://github.com/your-repo/nanobot/archive/refs/tags/v0.1.4.zip
unzip nanobot.zip
```

---

## 三、创建虚拟环境（推荐）

### Windows PowerShell

```powershell
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.venv\Scripts\Activate.ps1

# 或使用 cmd
.venv\Scripts\activate.bat
```

### macOS / Linux

```bash
# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate
```

---

## 四、安装依赖

### 基础依赖（必需）

```bash
# 方式一：从源码安装（推荐开发使用）
pip install -e .

# 方式二：使用 uv（推荐生产使用）
pip install uv
uv tool install nanobot-ai

# 方式三：从 PyPI 安装
pip install nanobot-ai
```

### Web UI 依赖（必需）

```bash
pip install fastapi uvicorn python-multipart
```

### 可选功能依赖

```bash
# 知识库检索（向量搜索）
pip install nanobot-ai[knowledge]

# PDF 支持
pip install nanobot-ai[pdf]

# Excel 支持
pip install nanobot-ai[excel]

# PPT 支持
pip install nanobot-ai[pptx]

# Word 支持
pip install nanobot-ai[docx]

# 浏览器自动化
pip install nanobot-ai[browser]

# OCR 支持
pip install nanobot-ai[ocr]

# 组合安装
pip install nanobot-ai[knowledge,pdf,excel,pptx,docx,browser,ocr]
```

---

## 五、配置文件

### 1. 创建配置目录

```bash
# Windows / macOS / Linux
mkdir -p ~/.nanobot
```

### 2. 首次运行初始化

```bash
# 运行 onboard 命令进行首次配置
python -m nanobot onboard

# 或直接运行
nanobot onboard
```

这会引导你设置：
- LLM Provider（选择模型供应商）
- API Key
- 渠道配置（飞书/钉钉/Telegram 等）

### 3. 配置文件位置

| 文件 | 位置 | 说明 |
|-----|------|------|
| 主配置 | `~/.nanobot/config.json` | 主要配置 |
| 角色配置 | `~/.nanobot/roles.yaml` | Agent 角色定义 |
| 白名单 | `~/.nanobot/whitelist.json` | MCP 命令白名单 |

---

## 六、运行服务

### 方式一：只运行 Gateway（核心服务）

```bash
# 默认端口 18790
python -m nanobot gateway

# 指定端口
python -m nanobot gateway --port 8080

# 调试模式（显示详细日志）
python -m nanobot gateway --verbose
```

### 方式二：同时运行 Gateway + Web UI

```bash
# 需要先安装 Web UI 依赖
pip install fastapi uvicorn python-multipart

# 运行（Web UI 端口默认 8080）
python -m nanobot gateway

# 启动后会同时启动 Web 服务
# Gateway: ws://localhost:18790
# Web UI: http://localhost:8080
```

### 方式三：Docker 运行

```bash
# 构建镜像
docker build -t nanobot .

# 运行容器
docker run -d -p 18790:18790 -p 8080:8080 \
  -v ~/.nanobot:/root/.nanobot \
  --name nanobot nanobot

# 使用 docker-compose（推荐）
docker-compose up -d
```

---

## 七、验证运行

### 1. 检查服务是否启动

```bash
# Gateway WebSocket
ws://localhost:18790

# Web UI
curl http://localhost:8080/api/health
```

### 2. 访问 Web UI

打开浏览器访问：`http://localhost:8080`

---

## 八、后台运行

### Windows

```powershell
# 使用 PowerShell 脚本
.\nanobot-service.ps1 -Action Start

# 或使用计划任务
```

### Linux / macOS

```bash
# 使用 nohup
nohup python -m nanobot gateway > /var/log/nanobot.log 2>&1 &

# 使用 systemd（Linux）
# 创建 /etc/systemd/system/nanobot.service
sudo systemctl start nanobot
sudo systemctl enable nanobot

# 使用 launchd（macOS）
# 创建 ~/Library/LaunchAgents/nanobot.plist
launchctl load ~/Library/LaunchAgents/nanobot.plist
```

---

## 九、常见问题

### Q: 修改代码后需要重新安装吗？

```bash
# 如果是 editable 模式安装 (pip install -e .)
# 代码修改后直接生效，无需重新安装

# 如果需要强制重载
# 重启服务即可
```

### Q: 端口被占用？

```bash
# 查看端口占用
netstat -tulpn | grep 18790    (Linux)
netstat -ano | findstr 18790    (Windows)

# 使用其他端口
python -m nanobot gateway --port 18791
```

### Q: 缺少依赖？

```bash
# 检查已安装的包
pip list | grep nanobot

# 重新安装
pip install -e . --force-reinstall
```

---

## 十、服务架构

```
┌─────────────────────────────────────────────────────────────┐
│                    NanoBot 服务架构                          │
└─────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │   Web UI (8080)  │
                    │   Vue.js SPA     │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  FastAPI (Web)  │
                    │   /api/*        │
                    └────────┬─────────┘
                             │
┌───────────────────────────┼───────────────────────────────┐
│                    ┌──────▼──────┐                         │
│                    │   Gateway   │                         │
│                    │  (18790)    │                         │
│                    └──────┬──────┘                         │
│                           │                                │
│         ┌────────────────┼────────────────┐               │
│         │                │                │               │
│    ┌────▼────┐     ┌─────▼─────┐    ┌─────▼─────┐       │
│    │ Channel │     │   Agent   │    │  Cron    │       │
│    │ Manager │     │   Loop    │    │ Service  │       │
│    └────┬────┘     └─────┬─────┘    └──────────┘       │
│         │                │                                │
│    ┌────▼────┐     ┌─────▼─────┐                        │
│    │ 飞书/   │     │  LLM      │                        │
│    │ 钉钉/   │     │ Provider  │                        │
│    │ Telegram│     └───────────┘                        │
│    └─────────┘                                           │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 十一、端口说明

| 端口 | 服务 | 说明 |
|-----|------|------|
| 18790 | Gateway | WebSocket 服务，主要通信端口 |
| 8080 | Web UI | HTTP 服务，管理界面 |

---

## 十二、快速启动命令汇总

```bash
# 1. 克隆项目
git clone https://github.com/xxx/nanobot.git
cd nanobot

# 2. 创建虚拟环境
python -m venv .venv

# 3. 激活虚拟环境
# Windows:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# 4. 安装基础依赖
pip install -e .
pip install fastapi uvicorn python-multipart

# 5. 初始化配置
python -m nanobot onboard

# 6. 启动服务
python -m nanobot gateway

# 7. 访问 Web UI
# 浏览器打开: http://localhost:8080
```

---

**注意**：首次运行 `python -m nanobot onboard` 时，系统会引导你完成配置，包括选择 LLM 提供商、输入 API Key、配置渠道等。
