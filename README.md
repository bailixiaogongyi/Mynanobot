# AiMate 系统文档

## 目录

- [系统概述](#系统概述)
- [系统架构](#系统架构)
- [核心模块](#核心模块)
- [快速开始](#快速开始)
- [安装部署完整指南](#安装部署完整指南)
  - [一、安装](#一安装)
  - [二、初始化配置](#二初始化配置)
  - [三、配置 API Key](#三配置-api-key)
  - [四、启动服务](#四启动服务)
  - [五、访问 Web UI](#五访问-web-ui)
  - [六、卸载](#六卸载)
  - [七、更新](#七更新)
  - [八、常用命令速查](#八常用命令速查)
- [常见问题与解决方案](#常见问题与解决方案)
- [验证安装](#验证安装)
- [初始化检查清单](#初始化检查清单)
- [配置说明](#配置说明)
- [国内环境适配](#国内环境适配)
  - [博查搜索](#博查搜索-web-search)
  - [心知天气](#心知天气-weather)
  - [知识索引模型下载](#知识索引模型下载)
- [部署指南](#部署指南)
- [Windows 后台服务](#windows-后台服务)
- [注意事项](#注意事项)
- [故障排除](#故障排除)

---

## 系统概述

**AiMate** 是一个超轻量级的个人 AI 助手框架，核心代码仅约 4,000 行。它提供了一个完整的 AI Agent 解决方案，支持多渠道接入、多 LLM 提供商、工具调用、记忆系统和知识检索等功能。

### 核心特性

| 特性                    | 描述                                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------------------- |
| 🪶 **超轻量**           | 核心代码 ~4,000 行，启动快速，资源占用低                                                                |
| 🔌 **多渠道**           | 支持 Telegram、Discord、WhatsApp、飞书、Slack、QQ、邮件等                                               |
| 🤖 **多模型**           | 支持 OpenRouter、Anthropic、OpenAI、DeepSeek、Gemini 等 20+ 提供商，含 SCNet、Qiniu、Baishan 国内提供商 |
| 🛠️ **工具调用**         | 内置文件操作、Shell 执行、网络搜索、天气查询、MCP 协议、浏览器脚本执行器等工具                          |
| 🧠 **记忆系统**         | 双层记忆架构（长期记忆 + 历史日志）                                                                     |
| 📚 **知识检索**         | 混合检索（BM25 + 向量），支持笔记索引                                                                   |
| ⏰ **定时任务**         | Cron 表达式和间隔调度                                                                                   |
| 🌐 **Web UI**           | FastAPI + Vue 3 现代化界面，支持配置管理                                                                |
| 🔐 **安全认证**         | 固定密码 + 设备指纹白名单，保护 Web UI 访问安全                                                         |
| 🇨🇳 **国内适配**         | 博查搜索、心知天气，完美支持国内网络环境                                                                |
| 🖥️ **浏览器脚本执行器** | 用户定义JSON脚本，AI调度执行                                                                            |

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                           用户交互层                                  │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────────┤
│   CLI       │  Telegram   │  Discord    │  WhatsApp   │   Web UI    │
│  (命令行)    │   (Bot)     │   (Bot)     │  (Bridge)   │  (FastAPI)  │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┘
       │             │             │             │             │
       └─────────────┴──────┬──────┴─────────────┴─────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         消息总线 (MessageBus)                         │
│                    入站消息 ←→ 出站消息路由                            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Agent Loop (核心代理循环)                      │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ Context     │→ │   LLM       │→ │   Tool      │→ │  Response   │ │
│  │ Builder     │  │  Provider   │  │  Executor   │  │  Generator  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       │                       │                       │
       ▼                       ▼                       ▼
┌─────────────┐        ┌─────────────┐        ┌─────────────┐
│   Memory    │        │   Tools     │        │  Knowledge  │
│   Store     │        │  Registry   │        │  Retriever  │
├─────────────┤        ├─────────────┤        ├─────────────┤
│ MEMORY.md   │        │ ReadFile    │        │ BM25 Index  │
│ HISTORY.md  │        │ WriteFile   │        │ Vector DB   │
│ Sessions    │        │ Exec        │        │ Note Proc   │
└─────────────┘        │ WebSearch   │        └─────────────┘
                       │ Weather     │
                       │ Browser     │
                       │ MCP Tools   │
                       └─────────────┘
```

### 数据流说明

1. **入站消息**: 用户通过各渠道发送消息 → Channel 接收 → 发布到 MessageBus
2. **Agent 处理**: AgentLoop 消费消息 → 构建上下文 → 调用 LLM → 执行工具 → 生成响应
3. **出站消息**: 响应发布到 MessageBus → Channel 消费 → 发送到用户

---

## 核心模块

### 1. Agent 模块 (`nanobot/agent/`)

核心代理逻辑，负责 LLM 交互和工具执行。

| 文件                  | 功能                             |
| --------------------- | -------------------------------- |
| `loop.py`             | Agent 主循环，消息处理，工具调用 |
| `context.py`          | 上下文构建，Prompt 模板管理      |
| `memory.py`           | 记忆存储和知识管理               |
| `skills.py`           | 技能加载器                       |
| `subagent_manager.py` | 后台任务执行器（v2）             |
| `mem_indexer.py`      | 记忆索引器                       |
| `mem_layer.py`        | 记忆层级管理                     |
| `tools/`              | 内置工具实现                     |

#### 子代理系统 (Subagent)

AiMate 支持子代理（Subagent）系统，用于并行处理复杂任务。

**配置方式**:

```json
{
  "agents": {
    "subagent": {
      "enabled": true,
      "version": "v2",
      "max_concurrent": 5,
      "default_timeout": 600,
      "workspace_isolation": true,
      "progress_report_interval": 10
    }
  }
}
```

**角色配置文件**:

子代理角色定义在 `roles.yaml` 文件中，包含以下预定义角色：

| 角色              | 名称         | 功能                         |
| ----------------- | ------------ | ---------------------------- |
| `document_writer` | 文档编写专家 | 编写各类技术文档、报告、方案 |
| `code_developer`  | 代码开发专家 | 编写、调试和优化代码         |
| `data_analyst`    | 数据分析专家 | 数据处理、分析和可视化       |
| `researcher`      | 研究分析专家 | 信息收集、专题研究           |

**角色文件位置**（优先级从高到低）：

1. 项目内置：`nanobot/config/roles.yaml`
2. 用户配置：`~/.nanobot/roles.yaml`（首次运行 `nanobot onboard` 时自动创建）

使用子代理时，主Agent会自动调用 `spawn` 工具创建子Agent，或通过API `/api/agents/spawn` 直接创建。

#### 角色系统 (Roles)

支持为不同场景定义专属角色，配置不同的模型参数。

**配置方式**:

```json
{
  "agents": {
    "roles": {
      "coder": {
        "enabled": true,
        "config": {
          "model": "anthropic/claude-sonnet-4-20250514",
          "temperature": 0.2,
          "max_tokens": 8192
        }
      },
      "writer": {
        "enabled": true,
        "config": {
          "model": "deepseek/deepseek-chat",
          "temperature": 0.7,
          "max_tokens": 16384
        }
      }
    }
  }
}
```

#### 任务系统 (Tasks)

支持任务规划、进度跟踪和反思机制。

| 组件                  | 功能           |
| --------------------- | -------------- |
| `tasks/planner.py`    | 任务规划器     |
| `tasks/tracker.py`    | 进度跟踪器     |
| `tasks/reflection.py` | 任务反思与总结 |

### 2. Channels 模块 (`nanobot/channels/`)

多渠道消息接入。

| 渠道     | 协议             | 特点                        |
| -------- | ---------------- | --------------------------- |
| Telegram | Long Polling     | 推荐，稳定可靠              |
| Discord  | WebSocket        | 需要 Message Content Intent |
| WhatsApp | Bridge (Node.js) | 需要扫码登录                |
| Feishu   | WebSocket 长连接 | 无需公网 IP                 |
| Slack    | Socket Mode      | 无需公网 IP                 |
| DingTalk | Stream Mode      | 无需公网 IP                 |
| QQ       | botpy SDK        | 仅支持私聊                  |
| Email    | IMAP/SMTP        | 需要应用专用密码            |
| Mochat   | WebSocket        | 企业微信/微信支持           |

### 3. Providers 模块 (`nanobot/providers/`)

LLM 提供商抽象层，基于 LiteLLM 实现。

```
Provider Registry (registry.py)
    ├── OpenRouter (推荐，支持所有模型)
    ├── Anthropic (Claude 直连)
    ├── OpenAI (GPT 直连)
    ├── DeepSeek
    ├── Gemini
    ├── Zhipu (智谱)
    ├── DashScope (通义千问)
    ├── Moonshot (Kimi)
    ├── MiniMax
    ├── VolcEngine (火山引擎)
    ├── SiliconFlow (硅基流动)
    ├── AIHubMix (多模型聚合)
    ├── SCNet (国家超算互联网)
    ├── Qiniu (七牛云)
    ├── Baishan (白山智算)
    ├── vLLM (本地部署)
    ├── Ollama (本地部署)
    ├── OpenAI Codex (ChatGPT OAuth)
    ├── GitHub Copilot (Copilot OAuth)
    └── Custom (自定义 OpenAI 兼容端点)
```

#### OpenAI Codex Provider

通过 OAuth 认证使用 ChatGPT 的 Codex Responses API。

**配置方式**:

```json
{
  "providers": {
    "openai_codex": {
      "api_key": ""
    }
  }
}
```

**使用前需要**:

1. 安装 `oauth-cli-kit` 包
2. 运行 `nanobot provider login openai_codex` 进行 OAuth 认证
3. 认证成功后可使用 `openai-codex/gpt-5.1-codex` 等模型

#### GitHub Copilot Provider

通过 OAuth 认证使用 GitHub Copilot。

**配置方式**:

```json
{
  "providers": {
    "github_copilot": {
      "api_key": ""
    }
  }
}
```

**使用前需要**:

1. 拥有 GitHub Copilot 订阅
2. 运行 `nanobot provider login github_copilot` 进行 OAuth 认证

### 4. Tools 模块 (`nanobot/agent/tools/`)

内置工具实现。

| 工具             | 功能               | 备注                             |
| ---------------- | ------------------ | -------------------------------- |
| `filesystem.py`  | 文件读写、目录操作 | 支持工作空间限制，最大文件 500MB |
| `shell.py`       | Shell 命令执行     | 可配置超时和权限                 |
| `web.py`         | 网络搜索、网页抓取 | 使用博查搜索 API，已防护 SSRF    |
| `weather.py`     | 天气查询、天气预报 | 使用心知天气 API                 |
| `note_search.py` | 笔记搜索           |                                  |
| `cron.py`        | 定时任务管理       |                                  |
| `spawn.py`       | 后台任务           | 支持角色分配、优先级、上下文传递 |
| `message.py`     | 消息发送           |                                  |
| `mcp.py`         | MCP 协议工具       | 支持外部 MCP 服务器              |
| `browser.py`     | 浏览器脚本执行器   | 用户定义JSON脚本，AI调度执行     |
| `docx.py`        | Word 文档处理      | 支持读取和创建 Word 文档         |
| `pdf.py`         | PDF 文档处理       | 支持读取文本、提取图片和表格     |
| `excel.py`       | Excel 表格处理     | 支持读写数据、工作表管理         |
| `pptx.py`        | PowerPoint 处理    | 支持读取、创建、添加幻灯片       |
| `ocr.py`         | OCR 文字识别       | 支持图片和PDF文字识别            |
| `return_file.py` | 文件下载           | 支持文件下载和保存               |

#### 技能系统 (Skills)

AiMate 支持技能（Skills）扩展机制，允许用户自定义 AI 能力。

**内置技能目录**: `nanobot/skills/`

| 技能名称             | 功能描述           |
| -------------------- | ------------------ |
| `daily-note`         | 日记管理           |
| `project-note`       | 项目笔记           |
| `topic-note`         | 主题笔记           |
| `temp-note`          | 临时笔记           |
| `memory`             | 记忆系统           |
| `skill-creator`      | 技能创建工具       |
| `browser-automation` | 浏览器自动化       |
| `github`             | GitHub 集成        |
| `summarize`          | 文本摘要           |
| `weather`            | 天气查询           |
| `cron`               | 定时任务           |
| `tmux`               | Tmux 会话管理      |
| `word-operations`    | Word 文档操作      |
| `pdf-operations`     | PDF 文档操作       |
| `excel-operations`   | Excel 表格操作     |
| `pptx-operations`    | PowerPoint 操作    |
| `ocr-operations`     | OCR 文字识别       |
| `archive`            | 文件归档           |
| `clawhub`            | ClawHub 浏览器集成 |

**自定义技能**: 用户可在 `~/.nanobot/workspace/skills/` 目录下创建自定义技能。

**技能格式**: 每个技能包含 `SKILL.md` 描述文件，定义技能名称、描述、触发词和实现逻辑。

#### 浏览器脚本执行器

用户预定义JSON脚本，AI调度执行自动化任务。

**核心理念**：

用户定义脚本 → AI理解脚本能力 → 按需调用执行 → 返回结果

**支持的脚本格式**：

| 格式        | 扩展名 | 特点                       |
| ----------- | ------ | -------------------------- |
| JSON 脚本   | .json  | 声明式配置，易于生成和编辑 |
| Python 脚本 | .py    | 灵活强大，支持复杂逻辑     |

**脚本目录**：

初始化后脚本目录: `~/.nanobot/browser/scripts/`

**使用示例**：

```
用户: "帮我登录CRM系统"
AI:   匹配到 crm 脚本，执行登录流程...

用户: "查询异常工时记录"
AI:   匹配到 crm 脚本，执行查询操作...

用户: "列出所有可用脚本"
AI:   返回脚本列表...
```

**三种执行模式**：

| 模式       | 说明                     | 适用场景               |
| ---------- | ------------------------ | ---------------------- |
| `headed`   | 有头模式，显示浏览器窗口 | 学习、调试、首次执行   |
| `headless` | 无头模式，后台执行       | 日常自动化、不影响工作 |
| `debug`    | 调试模式，慢速+可见      | 观察执行细节、排查问题 |

**依赖安装**：

浏览器依赖会在首次使用时自动安装，无需手动操作。如需提前安装：

```bash
# 手动安装 Chromium 浏览器
playwright install chromium

# Linux 系统可能还需要安装系统依赖
playwright install-deps chromium
```

**数据存储**：

- 脚本目录: `~/.nanobot/browser/scripts/`
- 截图: `~/.nanobot/browser/screenshots/`

#### MCP 工具协议

支持连接外部 MCP (Model Context Protocol) 服务器，扩展工具能力。

**配置方式**:

```json
{
  "tools": {
    "mcp_servers": {
      "filesystem": {
        "command": "npx",
        "args": [
          "-y",
          "@modelcontextprotocol/server-filesystem",
          "/path/to/allowed/dir"
        ],
        "tool_timeout": 30
      },
      "custom-server": {
        "url": "http://localhost:3000/mcp",
        "headers": { "Authorization": "Bearer token" },
        "tool_timeout": 60
      }
    }
  }
}
```

**安全说明**:

- MCP 服务器命令有白名单限制，只允许 `npx`, `node`, `python`, `uvx` 等安全命令
- 生产环境建议启用 `restrict_to_workspace` 配置

### 5. Knowledge 模块 (`nanobot/knowledge/`)

知识检索系统，支持混合检索。

```
HybridRetriever
    ├── BM25Retriever (关键词检索)
    ├── VectorStore (语义检索)
    ├── GraphStore (知识图谱 - 可选)
    └── RRF Fusion (倒数排名融合)
```

**知识库索引配置**:

```json
{
  "tools": {
    "knowledge": {
      "index": {
        "enabled": true,
        "embedding_model": "BAAI/bge-small-zh-v1.5",
        "persist_dir": "~/.nanobot/knowledge",
        "chunk_size": 512,
        "chunk_overlap": 50,
        "use_bm25": true,
        "use_vector": true,
        "use_graph": false,
        "rrf_k": 60
      },
      "search": {
        "default_top_k": 5,
        "cache_enabled": true,
        "cache_max_size": 100,
        "cache_ttl_seconds": 3600,
        "default_search_type": "auto"
      },
      "auto_index_notes": true,
      "notes_dirs": ["daily", "projects", "personal", "topics", "pending"]
    }
  }
}
```

**高级知识配置**（可选 - 需要安装知识库依赖）:

```json
{
  "tools": {
    "knowledge": {
      "index": {
        "enabled": true,
        "use_graph": true,
        "use_llm_extract": true,
        "llm_extract_batch": 10,
        "llm_extract_threshold": 0.7,
        "fallback_on_llm_error": true
      }
    }
  }
}
```

**配置项说明**:

| 配置项                  | 说明                 | 默认值                   |
| ----------------------- | -------------------- | ------------------------ |
| `index.enabled`         | 是否启用知识索引     | `true`                   |
| `index.embedding_model` | 嵌入模型             | `BAAI/bge-small-zh-v1.5` |
| `index.persist_dir`     | 索引持久化目录       | `~/.nanobot/knowledge`   |
| `index.chunk_size`      | 文本分块大小         | 512                      |
| `index.chunk_overlap`   | 分块重叠字符数       | 50                       |
| `index.use_bm25`        | 启用 BM25 关键词检索 | `true`                   |
| `index.use_vector`      | 启用向量语义检索     | `true`                   |
| `index.use_graph`       | 启用知识图谱检索     | `false`                  |
| `index.use_llm_extract` | 启用 LLM 实体提取    | `false`                  |
| `search.default_top_k`  | 默认返回结果数       | 5                        |
| `search.cache_enabled`  | 启用搜索缓存         | `true`                   |
| `auto_index_notes`      | 自动索引笔记目录     | `true`                   |

**安装知识库依赖**:

```bash
pip install nanobot-ai[knowledge]
```

**可选：安装 Word 文档支持**:

```bash
pip install nanobot-ai[docx]
```

**安全说明**:

- BM25 索引使用 HMAC 签名验证，防止文件篡改
- 可通过环境变量 `NANOBOT_PERSISTENCE_SECRET` 设置签名密钥

### 6. Web 模块 (`nanobot/web/`)

Web UI 和 API 服务。

```
FastAPI Application
    ├── /api/auth/*    认证接口（登录、验证、状态）
    ├── /api/chat/*    聊天接口
    ├── /api/notes/*   笔记管理
    ├── /api/skills/*  技能管理
    ├── /api/config/*  配置管理（支持 Web 端修改 API Key）
    ├── /api/agents/*  代理管理
    ├── /api/upload/*  文件上传
    └── /              静态文件 (Vue 3 SPA)
```

### 7. 会话管理模块 (`nanobot/session/`)

会话管理服务，维护用户对话状态。

```
SessionManager
    ├── 会话存储 (~/.nanobot/sessions/)
    ├── 上下文管理
    └── 消息历史
```

### 8. 定时任务模块 (`nanobot/cron/`)

定时任务调度系统，支持 Cron 表达式和间隔调度。

```
CronService
    ├── CronSchedule: Cron 表达式调度
    ├── IntervalSchedule: 间隔调度
    └── OneTimeSchedule: 一次性调度
```

**配置方式**:

```json
{
  "gateway": {
    "heartbeat": {
      "enabled": true,
      "interval_s": 1800
    }
  }
}
```

### 9. 心跳服务模块 (`nanobot/heartbeat/`)

定期任务执行服务，可定时运行 AI 任务。

**配置方式**:

```json
{
  "gateway": {
    "heartbeat": {
      "enabled": true,
      "interval_s": 1800 // 每30分钟执行一次
    }
  }
}
```

### 10. 消息总线模块 (`nanobot/bus/`)

消息路由和事件系统。

```
MessageBus
    ├── InboundQueue: 入站消息队列
    ├── OutboundQueue: 出站消息队列
    ├── PubSub: 发布订阅
    └── Events: 事件类型定义
```

### 11. 上传模块 (`nanobot/upload/`)

文件上传管理。

**配置方式**:

```json
{
  "upload": {
    "enabled": true,
    "max_file_size": 20971520, // 20MB
    "allowed_image_types": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"],
    "allowed_doc_types": [
      ".pdf",
      ".doc",
      ".docx",
      ".txt",
      ".md",
      ".csv",
      ".xlsx",
      ".xls"
    ]
  }
}
```

### 7. Web UI 安全认证

Web UI 支持基于固定密码 + 设备指纹白名单的安全认证机制。

**认证流程**:

```
用户访问 Web UI
    │
    ▼
检查设备指纹是否在白名单
    │
    ├── 在白名单 → 直接放行
    │
    └── 不在白名单 → 跳转登录页
                        │
                        ▼
                   输入固定密码
                        │
                        ├── 密码正确 → 指纹写入白名单 → 放行
                        │
                        └── 密码错误 → 拒绝访问
```

**配置方式**:

```json
{
  "gateway": {
    "web_ui": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8080,
      "auth": {
        "enabled": true,
        "password": "",
        "whitelist_file": "~/.nanobot/whitelist.json"
      }
    }
  }
}
```

**配置项说明**:

| 配置项                | 说明                           | 默认值                      |
| --------------------- | ------------------------------ | --------------------------- |
| `auth.enabled`        | 是否启用认证                   | `false`                     |
| `auth.password`       | 固定访问密码（为空时自动生成） | `""`                        |
| `auth.whitelist_file` | 白名单文件路径                 | `~/.nanobot/whitelist.json` |

**密码自动生成**:

当 `auth.enabled` 为 `true` 且 `auth.password` 为空时，系统会在首次启动时自动生成一个 24 位安全密码：

- 包含大小写字母、数字和特殊符号
- 使用加密安全的随机数生成器
- 密码会自动保存到配置文件中
- **密码仅在启动日志中显示一次，请务必保存**

启动日志示例：

```
============================================================
WEB UI AUTHENTICATION PASSWORD GENERATED
Password: xK9#mP2$vL7@nQ4!wR8&yT3
Please save this password securely!
It will NOT be shown again.
============================================================
```

**运维操作**:

| 操作         | 方法                                    |
| ------------ | --------------------------------------- |
| 添加新设备   | 新用户在浏览器输入一次密码即可          |
| 移除设备     | 编辑 `whitelist.json`，删除对应指纹哈希 |
| 更换密码     | 修改配置文件中的 `password`，重启服务   |
| 重置所有设备 | 删除 `whitelist.json` 文件              |

**安全特性**:

- 设备指纹基于浏览器特征生成（UserAgent、屏幕、Canvas等）
- 指纹经 SHA-256 哈希后存储，不存储明文
- 白名单持久化存储，重启服务不丢失
- 前端无管理入口，仅服务器后台可管理
- 密码验证使用恒定时间比较，防止时序攻击
- 登录失败 5 次后锁定 5 分钟，防止暴力破解

---

## 快速开始

### 环境要求

- Python >= 3.11
- Node.js >= 18 (仅 WhatsApp 需要)
- Docker (可选，推荐生产使用)

### 安装方式

**方式一：从源码安装（推荐开发使用）**

```bash
git clone https://github.com/HKUDS/nanobot.git
cd nanobot
pip install -e .

或者使用：
python3 -m pip install -e .
```

**方式二：使用 uv 安装（推荐生产使用）**

```bash
uv tool install nanobot-ai
```

**方式三：从 PyPI 安装**

```bash
pip install nanobot-ai
```

---

## 安装部署完整指南

### 环境要求

| 项目     | 要求                            |
| -------- | ------------------------------- |
| Python   | >= 3.11                         |
| Node.js  | >= 18（仅 WhatsApp 需要，可选） |
| 操作系统 | Linux / Windows / macOS         |

---

### 一、安装

#### 方式一：从源码安装（推荐开发使用）

**Linux：**

```bash
# 1. 克隆源码
git clone https://github.com/HKUDS/nanobot.git
cd nanobot

# 2. 创建虚拟环境
python3 -m venv .venv

# 3. 激活虚拟环境
source .venv/bin/activate

# 4. 安装（可编辑模式）
python3 -m pip install -e .

# 5. 安装 Web UI 依赖（必需）
pip install fastapi uvicorn python-multipart

# 6. 验证安装
nanobot --version
```

**Windows：**

```powershell
# 1. 克隆源码
git clone https://github.com/HKUDS/nanobot.git
cd nanobot

# 2. 创建虚拟环境
python -m venv .venv

# 3. 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 4. 安装（可编辑模式）
pip install -e .

# 5. 安装 Web UI 依赖（必需）
pip install fastapi uvicorn python-multipart

# 6. 验证安装
nanobot --version
```

#### 方式二：使用 uv 安装（推荐生产使用）

**Linux：**

```bash
# 1. 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 安装 nanobot
uv tool install nanobot-ai

# 3. 验证安装
nanobot --version
```

**Windows：**

```powershell
# 1. 安装 uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. 安装 nanobot
uv tool install nanobot-ai

# 3. 验证安装
nanobot --version
```

#### 方式三：从 PyPI 安装

```bash
pip install nanobot-ai
```

**可选依赖**：

| 依赖组      | 功能                 | 安装命令                            |
| ----------- | -------------------- | ----------------------------------- |
| `knowledge` | 知识索引（向量检索） | `pip install nanobot-ai[knowledge]` |
| `docx`      | Word 文档处理        | `pip install nanobot-ai[docx]`      |
| `pdf`       | PDF 文档处理         | `pip install nanobot-ai[pdf]`       |
| `excel`     | Excel 表格处理       | `pip install nanobot-ai[excel]`     |
| `pptx`      | PowerPoint 处理      | `pip install nanobot-ai[pptx]`      |
| `ocr`       | OCR 文字识别         | `pip install nanobot-ai[ocr]`       |
| `web-ui`    | Web UI 界面          | `pip install nanobot-ai[web-ui]`    |

可以组合安装：`pip install nanobot-ai[pdf,excel,pptx,ocr]`

---

### 二、初始化配置

```bash
# 初始化配置和工作空间
nanobot onboard
```

`onboard` 命令会创建：

- 配置文件：`~/.nanobot/config.json`
- 工作空间目录：`daily/`, `projects/`, `personal/`, `topics/`, `pending/`, `memory/`, `skills/`
- 模板文件：`MEMORY.md`, `HISTORY.md` 等

---

### 三、配置 API Key

编辑配置文件，添加至少一个 Provider 的 API Key：

```bash
# Linux
nano ~/.nanobot/config.json

# Windows
notepad %USERPROFILE%\.nanobot\config.json
```

最小配置示例：

```json
{
  "providers": {
    "deepseek": {
      "api_key": "sk-xxx"
    }
  }
}
```

#### 支持的 LLM 提供商

| 提供商      | 环境变量             | 配置字段                | 说明           |
| ----------- | -------------------- | ----------------------- | -------------- |
| OpenAI      | `OPENAI_API_KEY`     | `providers.openai`      | GPT 模型       |
| Anthropic   | `ANTHROPIC_API_KEY`  | `providers.anthropic`   | Claude 模型    |
| DeepSeek    | `DEEPSEEK_API_KEY`   | `providers.deepseek`    | DeepSeek 模型  |
| Gemini      | `GOOGLE_API_KEY`     | `providers.gemini`      | Google Gemini  |
| Zhipu       | `ZAI_API_KEY`        | `providers.zhipu`       | 智谱 GLM       |
| DashScope   | `DASHSCOPE_API_KEY`  | `providers.dashscope`   | 通义千问       |
| Moonshot    | `MOONSHOT_API_KEY`   | `providers.moonshot`    | Kimi           |
| MiniMax     | `MINIMAX_API_KEY`    | `providers.minimax`     | MiniMax        |
| OpenRouter  | `OPENROUTER_API_KEY` | `providers.openrouter`  | 全球模型网关   |
| SiliconFlow | `OPENAI_API_KEY`     | `providers.siliconflow` | 硅基流动       |
| VolcEngine  | `OPENAI_API_KEY`     | `providers.volcengine`  | 火山引擎       |
| SCNet       | `SCNET_API_KEY`      | `providers.scnet`       | 国家超算互联网 |
| Qiniu       | `QINIU_API_KEY`      | `providers.qiniu`       | 七牛云         |
| Baishan     | `BAISHAN_API_KEY`    | `providers.baishan`     | 白山智算       |

**注意**：SCNet、Qiniu、Baishan 为国内优化线路，适合国内用户使用。

---

### 四、启动服务

#### 前台运行（调试用）

```bash
nanobot gateway
```

#### 后台运行

**Linux（Systemd）：**

```bash
# 1. 查看当前路径
pwd

# 2. 创建服务文件（替换 /path/to/nanobot 为实际路径）
cat > ~/.config/systemd/user/nanobot-gateway.service << 'EOF'
[Unit]
Description=Nanobot Gateway
After=network.target

[Service]
Type=simple
ExecStart=/path/to/nanobot/.venv/bin/nanobot gateway
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

# 3. 启动服务
systemctl --user daemon-reload
systemctl --user enable --now nanobot-gateway

# 4. 查看状态
systemctl --user status nanobot-gateway

# 5. 查看日志
journalctl --user -u nanobot-gateway -f
```

**Windows：**

```powershell
# 方式一：批处理文件
.\start_nanobot.bat    # 启动
.\stop_nanobot.bat     # 停止

# 方式二：PowerShell 脚本
.\nanobot-service.ps1 start    # 启动
.\nanobot-service.ps1 stop     # 停止
.\nanobot-service.ps1 restart  # 重启
.\nanobot-service.ps1 status   # 查看状态
```

---

### 五、访问 Web UI

浏览器访问：`http://服务器IP:8080`

- **Web UI 端口**: 8080 (默认)
- **Gateway API 端口**: 18790 (默认)

首次启动时，日志会显示自动生成的登录密码：

```
============================================================
WEB UI AUTHENTICATION PASSWORD GENERATED
Password: xK9#mP2$vL7@nQ4!wR8&yT3
Please save this password securely!
============================================================
```

---

### 六、卸载

**Linux：**

```bash
# uv 方式卸载
uv tool uninstall nanobot-ai

# pip 方式卸载
python3 -m pip uninstall nanobot-ai

# 清理残留
rm -rf ~/.local/bin/nanobot
rm -rf ~/.nanobot    # 清理配置（可选）
rm -rf .venv         # 清理虚拟环境（可选）
```

**Windows：**

```powershell
# uv 方式卸载
uv tool uninstall nanobot-ai

# pip 方式卸载
pip uninstall nanobot-ai

# 清理残留
Remove-Item -Recurse -Force "$env:USERPROFILE\.nanobot" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".venv" -ErrorAction SilentlyContinue
```

---

### 七、更新

**从源码更新：**

```bash
# 1. 进入源码目录
cd nanobot

# 2. 拉取最新代码
git pull

# 3. 激活虚拟环境
source .venv/bin/activate  # Linux
.\.venv\Scripts\Activate.ps1  # Windows

# 4. 重新安装
pip install -e .

# 5. 重启服务
```

**使用 uv 更新：**

```bash
uv tool upgrade nanobot-ai
```

---

### 八、常用命令速查

| 操作         | Linux                                     | Windows                                      |
| ------------ | ----------------------------------------- | -------------------------------------------- |
| 激活虚拟环境 | `source .venv/bin/activate`               | `.\.venv\Scripts\Activate.ps1`               |
| 初始化       | `nanobot onboard`                         | `nanobot onboard`                            |
| 前台启动     | `nanobot gateway`                         | `nanobot gateway`                            |
| 后台启动     | `systemctl --user start nanobot-gateway`  | `.\nanobot-service.ps1 start`                |
| 停止服务     | `systemctl --user stop nanobot-gateway`   | `.\nanobot-service.ps1 stop`                 |
| 查看状态     | `systemctl --user status nanobot-gateway` | `.\nanobot-service.ps1 status`               |
| 查看日志     | `journalctl --user -u nanobot-gateway -f` | 查看 `logs/` 目录                            |
| 配置文件     | `nano ~/.nanobot/config.json`             | `notepad %USERPROFILE%\.nanobot\config.json` |

---

## 常见问题与解决方案

### 1. Web UI 页面空白或数据不显示

**症状**：笔记、技能、配置页面显示空白

**原因**：浏览器 Console 显示 `TypeError: Cannot read properties of undefined (reading 'digest')`

**解决方案**：这是因为 `crypto.subtle` API 只在 HTTPS 或 localhost 环境下可用。已在新版本中修复。

**临时解决**：

- 使用 HTTPS 访问（推荐）
- 或使用 localhost 本地访问
- 或更新到最新版本

### 2. Web UI dependencies not installed

**症状**：日志显示 `Web UI dependencies not installed`

**解决方案**：

```bash
# 激活虚拟环境
source .venv/bin/activate  # Linux
.\.venv\Scripts\Activate.ps1  # Windows

# 安装依赖
pip install fastapi uvicorn python-multipart

# 重启服务
```

### 3. 无法绑定地址 (Errno 99)

**症状**：`error while attempting to bind on address ('x.x.x.x', 8080): cannot assign requested address`

**原因**：`gateway.webUi.host` 配置为公网 IP

**解决方案**：修改配置文件，将 `host` 改为 `0.0.0.0`

```json
{
  "gateway": {
    "webUi": {
      "host": "0.0.0.0"
    }
  }
}
```

### 4. No API key configured

**症状**：启动时报错 `No API key configured`

**解决方案**：编辑 `~/.nanobot/config.json`，添加至少一个 Provider 的 API Key

### 5. 版本缓存问题（代码修改后不生效）

**症状**：修改代码后重新安装，但行为未改变

**原因**：pip/uv 缓存了旧的构建

**解决方案**：

```bash
# 方式一：修改版本号后重新安装
# 编辑 pyproject.toml 和 nanobot/__init__.py 中的版本号
pip install -e .

# 方式二：使用虚拟环境的可编辑模式
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 6. 工作空间目录未创建

**症状**：笔记页面显示空白，但 API 返回目录列表

**原因**：旧版本 `onboard` 命令未创建子目录

**解决方案**：

```bash
# 手动创建目录
mkdir -p ~/.nanobot/workspace/{daily,projects,personal,topics,pending,memory,skills}

# 或重新运行 onboard
nanobot onboard
```

### 7. 技能列表为空

**症状**：技能页面显示空白

**原因**：内置技能目录未正确安装

**解决方案**：

```bash
# 检查内置技能目录
ls nanobot/skills/  # 源码安装
ls .venv/lib/python*/site-packages/nanobot/skills/  # pip 安装

# 如果目录不存在，重新安装
pip install -e .
```

---

## 验证安装

### 检查服务状态

```bash
# Linux
systemctl --user status nanobot-gateway
journalctl --user -u nanobot-gateway -n 50

# Windows
.\nanobot-service.ps1 status
```

### 检查 API 端点

```bash
# 在服务器本地测试
curl http://localhost:8080/api/health
curl http://localhost:8080/api/notes/dirs
curl http://localhost:8080/api/skills/list
curl http://localhost:8080/api/config/
```

### 检查端口监听

```bash
# Linux
ss -tlnp | grep 8080

# Windows
netstat -an | findstr 8080
```

---

## 初始化检查清单

- [ ] Python >= 3.11 已安装 (`python --version`)
- [ ] 虚拟环境已创建并激活
- [ ] nanobot 已安装 (`pip install -e .` 或 `uv tool install nanobot-ai`)
- [ ] Web UI 依赖已安装 (`pip install fastapi uvicorn python-multipart`)
- [ ] `nanobot onboard` 已执行
- [ ] 配置文件已创建 (`~/.nanobot/config.json`)
- [ ] 至少一个 Provider API Key 已配置
- [ ] 工作空间目录已创建 (`~/.nanobot/workspace/`)
  - `daily/` - 每日笔记
  - `projects/` - 项目笔记
  - `personal/` - 个人笔记
  - `topics/` - 主题笔记
  - `pending/` - 待处理笔记
  - `memory/` - 记忆文件
  - `skills/` - 自定义技能
- [ ] 服务已启动 (`nanobot gateway` 或 systemd)
- [ ] Web UI 可访问 (`http://IP:8080`)
- [ ] 登录密码已记录（首次启动时显示）

### 可选：安装知识库依赖

如果需要使用知识索引功能：

```bash
pip install nanobot-ai[knowledge]
```

### 可选：安装浏览器自动化依赖

如果需要使用浏览器脚本功能：

```bash
playwright install chromium
```

---

Web UI 默认配置：

```json
{
  "gateway": {
    "webUi": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8080,
      "auth": {
        "enabled": true,
        "password": "",
        "whitelistFile": "~/.nanobot/whitelist.json"
      }
    }
  }
}
```

**重要配置说明**：

| 配置项          | 说明                              |
| --------------- | --------------------------------- |
| `host`          | 必须为 `0.0.0.0`，不能使用公网 IP |
| `auth.enabled`  | 默认不启用，需手动开启            |
| `auth.password` | 为空时，启动时自动生成 24 位密码  |

**首次启动时**，日志会显示自动生成的密码：

```
============================================================
WEB UI AUTHENTICATION PASSWORD GENERATED
Password: xK9#mP2$vL7@nQ4!wR8&yT3
Please save this password securely!
It will NOT be shown again.
============================================================
```

**关闭认证**（不推荐）：

```json
{
  "gateway": {
    "webUi": {
      "auth": {
        "enabled": false
      }
    }
  }
}
```

### 最小配置示例

```json
{
  "providers": {
    "deepseek": {
      "api_key": "sk-xxx"
    }
  },
  "tools": {
    "web": {
      "search": {
        "api_key": "你的博查搜索API密钥"
      }
    },
    "weather": {
      "weather": {
        "api_key": "你的心知天气API密钥"
      }
    }
  }
}
```

### 启动使用

```bash
# 命令行聊天
nanobot agent

# 启动网关（连接聊天渠道）
nanobot gateway

# 查看状态
nanobot status
```

---

## 启动流程

### CLI 模式启动流程

```
nanobot agent
    │
    ▼
┌─────────────────────────────────────┐
│ 1. 加载配置 (load_config)            │
│    - 读取 ~/.nanobot/config.json    │
│    - 验证配置有效性                   │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│ 2. 创建 LLM Provider                 │
│    - 根据模型匹配提供商               │
│    - 设置 API Key 和 Base URL       │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│ 3. 初始化 AgentLoop                  │
│    - 创建 MessageBus                │
│    - 注册工具 (ToolRegistry)         │
│    - 初始化会话管理器                 │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│ 4. 进入交互循环                       │
│    - 读取用户输入                     │
│    - 发布到消息总线                   │
│    - 等待响应并显示                   │
└─────────────────────────────────────┘
```

### Gateway 模式启动流程

```
nanobot gateway
    │
    ▼
┌─────────────────────────────────────┐
│ 1. 加载配置和创建 Provider            │
│    (同 CLI 模式)                      │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│ 2. 初始化服务组件                     │
│    - CronService (定时任务)          │
│    - HeartbeatService (心跳)         │
│    - SessionManager (会话)           │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│ 3. 初始化渠道管理器                   │
│    - 根据配置启用渠道                 │
│    - Telegram/Discord/WhatsApp 等   │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│ 4. 启动 Web UI (可选)                │
│    - FastAPI 服务                    │
│    - 端口 8080                       │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│ 5. 并发运行所有服务                   │
│    - AgentLoop (消息处理)            │
│    - ChannelManager (渠道连接)       │
│    - CronService (定时任务)          │
│    - HeartbeatService (心跳)         │
│    - WebServer (Web UI)             │
└─────────────────────────────────────┘
```

---

## 配置说明

### 配置文件位置

- 配置文件: `~/.nanobot/config.json`
- 工作空间: `~/.nanobot/workspace/`
- 会话数据: `~/.nanobot/sessions/`
- 记忆文件: `~/.nanobot/workspace/memory/`
- 知识库: `~/.nanobot/knowledge/`
- 定时任务: `~/.nanobot/cron/`

### 完整配置结构

```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.nanobot/workspace",
      "model": "anthropic/claude-opus-4-5",
      "max_tokens": 8192,
      "temperature": 0.1,
      "max_tool_iterations": 30,
      "memory_window": 50
    }
  },
  "providers": {
    "deepseek": {
      "api_key": "sk-xxx"
    },
    "openrouter": {
      "api_key": "sk-or-v1-xxx"
    }
  },
  "gateway": {
    "host": "0.0.0.0",
    "port": 18790,
    "heartbeat": {
      "enabled": true,
      "interval_s": 1800
    },
    "web_ui": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8080,
      "auth": {
        "enabled": false,
        "password": "",
        "whitelist_file": "~/.nanobot/whitelist.json"
      }
    }
  },
  "tools": {
    "web": {
      "search": {
        "api_key": "博查搜索API密钥",
        "max_results": 10
      }
    },
    "weather": {
      "weather": {
        "api_key": "心知天气API密钥"
      }
    },
    "exec": {
      "timeout": 60
    },
    "restrict_to_workspace": false,
    "mcp_servers": {},
    "knowledge": {
      "index": {
        "enabled": true,
        "embedding_model": "BAAI/bge-small-zh-v1.5"
      }
    }
  },
  "channels": {
    "send_progress": true,
    "send_tool_hints": false,
    "telegram": {
      "enabled": false,
      "token": "",
      "allow_from": []
    },
    "feishu": {
      "enabled": false,
      "app_id": "",
      "app_secret": ""
    }
  }
}
```

### 关键配置项说明

| 配置项                                | 说明                     | 默认值                      |
| ------------------------------------- | ------------------------ | --------------------------- |
| `agents.defaults.model`               | 默认 LLM 模型            | `anthropic/claude-opus-4-5` |
| `agents.defaults.max_tokens`          | 最大输出 token 数        | 8192                        |
| `agents.defaults.temperature`         | 生成温度                 | 0.1                         |
| `agents.defaults.max_tool_iterations` | 最大工具调用迭代次数     | 30                          |
| `agents.defaults.memory_window`       | 记忆窗口大小             | 50                          |
| `agents.defaults.enable_reasoning`    | 启用推理/思考输出        | true                        |
| `agents.subagent.enabled`             | 启用子代理系统           | true                        |
| `agents.subagent.max_concurrent`      | 最大并发子任务数         | 5                           |
| `agents.subagent.default_timeout`     | 子任务超时时间（秒）     | 600                         |
| `channels.send_progress`              | 是否发送进度更新         | true                        |
| `channels.send_tool_hints`            | 是否发送工具调用提示     | false                       |
| `tools.restrict_to_workspace`         | 是否限制工具访问工作空间 | false                       |
| `tools.exec.timeout`                  | Shell 执行超时（秒）     | 60                          |
| `tools.web.search.api_key`            | 博查搜索 API Key         | ""                          |
| `tools.web.search.max_results`        | 最大搜索结果数           | 10                          |
| `tools.weather.weather.api_key`       | 心知天气 API Key         | ""                          |
| `gateway.host`                        | Gateway 监听地址         | `0.0.0.0`                   |
| `gateway.port`                        | Gateway 监听端口         | 18790                       |
| `gateway.heartbeat.enabled`           | 启用心跳服务             | true                        |
| `gateway.heartbeat.interval_s`        | 心跳间隔（秒）           | 1800                        |
| `gateway.web_ui.enabled`              | 是否启用 Web UI          | true                        |
| `gateway.web_ui.host`                 | Web UI 监听地址          | `0.0.0.0`                   |
| `gateway.web_ui.port`                 | Web UI 端口              | 8080                        |
| `gateway.web_ui.auth.enabled`         | 是否启用 Web UI 认证     | false                       |
| `gateway.web_ui.auth.password`        | Web UI 访问密码          | ""                          |
| `upload.enabled`                      | 是否启用文件上传         | true                        |
| `upload.max_file_size`                | 最大上传文件大小（字节） | 20971520 (20MB)             |

---

## 国内环境适配

本项目已针对国内网络环境进行了适配，使用以下国内服务替代原有工具：

### 博查搜索 (Web Search)

**API 文档**: https://bocha-ai.feishu.cn/wiki/RXEOw02rFiwzGSkd9mUcqoeAnNK

**配置方式**:

```json
{
  "tools": {
    "web": {
      "search": {
        "api_key": "你的博查搜索API密钥"
      }
    }
  }
}
```

**获取 API Key**: 访问 https://bocha.ai 注册并获取

**功能特性**:

- 支持中文搜索
- 返回标题、摘要、链接、来源网站
- 支持时间范围过滤
- 支持长摘要

### 心知天气 (Weather)

**API 文档**: https://github.com/seniverse/seniverse-api-demos

**配置方式**:

```json
{
  "tools": {
    "weather": {
      "weather": {
        "api_key": "你的心知天气API密钥"
      }
    }
  }
}
```

**获取 API Key**: 访问 https://www.seniverse.com 注册并获取

**功能特性**:

- 实时天气查询
- 未来 15 天天气预报
- 支持多种位置格式（城市名、坐标、IP）
- 支持多语言

### 使用示例

```
用户: 搜索一下今天的科技新闻
助手: [调用 web_search 工具，使用博查搜索 API]

用户: 北京今天天气怎么样？
助手: [调用 weather 工具，使用心知天气 API]

用户: 上海未来三天天气预报
助手: [调用 weather_forecast 工具]
```

### 知识索引模型下载

笔记索引功能需要下载嵌入模型，用于语义搜索。

#### 模型信息

| 项目     | 说明                        |
| -------- | --------------------------- |
| 默认模型 | `BAAI/bge-small-zh-v1.5`    |
| 模型大小 | 约 100MB                    |
| 下载位置 | `~/.cache/huggingface/hub/` |

#### 国内镜像配置

无法连接 HuggingFace 时，使用国内镜像：

```bash
# 设置环境变量
export HF_ENDPOINT=https://hf-mirror.com

# 添加到配置文件（永久生效）
echo 'export HF_ENDPOINT=https://hf-mirror.com' >> ~/.bashrc
source ~/.bashrc
```

#### 预下载模型

```bash
# 安装依赖
pip install sentence-transformers

# 预下载模型
python3 -c "
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
print('模型下载成功')
"
```

#### 离线安装模型

在有网络的机器上下载后传输：

```bash
# 有网络的机器
tar -czvf huggingface_cache.tar.gz ~/.cache/huggingface/

# 传输到目标服务器
scp huggingface_cache.tar.gz user@server:/tmp/

# 目标服务器上解压
tar -xzvf /tmp/huggingface_cache.tar.gz -C ~/
```

#### 只使用 BM25（无需模型）

如果网络受限且不需要语义搜索，可以禁用向量索引：

```json
{
  "tools": {
    "knowledge": {
      "index": {
        "use_bm25": true,
        "use_vector": false
      }
    }
  }
}
```

| 索引类型 | 需要模型  | 说明           |
| -------- | --------- | -------------- |
| BM25     | ❌ 不需要 | 关键词精确匹配 |
| 向量索引 | ✅ 需要   | 语义相似度搜索 |

---

## 部署指南

### Docker 部署（推荐）

#### 部署架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        云服务器                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Docker 容器                            │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │              nanobot-gateway                       │  │   │
│  │  │   ┌─────────────┐    ┌─────────────┐              │  │   │
│  │  │   │  Web UI     │    │  Gateway    │              │  │   │
│  │  │   │  :8080      │    │  :18790     │              │  │   │
│  │  │   └─────────────┘    └─────────────┘              │  │   │
│  │  │   /root/.nanobot/ ◄── 挂载 ──► ~/.nanobot/        │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│                    ┌─────────────────┐                          │
│                    │  ~/.nanobot/    │                          │
│                    │  ├── config.json│                          │
│                    │  ├── workspace/ │                          │
│                    │  ├── knowledge/ │                          │
│                    │  └── cron/      │                          │
│                    └─────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

#### 快速部署步骤

```bash
# 1. 克隆项目，代码修改，不能克隆
# git clone https://github.com/HKUDS/nanobot.git
# cd nanobot

# 2. 构建镜像
docker compose build

# 3. 启动服务（自动创建默认配置）
docker compose up -d nanobot-gateway

# 4. 查看初始化日志
docker compose logs nanobot-gateway

# 5. 配置 API Key（两种方式）

# 方式A：通过 Web UI
# 访问 http://服务器IP:8080 → Settings → 配置 API Key

# 方式B：直接编辑配置文件
nano ~/.nanobot/config.json

# 6. 重启服务使配置生效
docker compose restart nanobot-gateway

# 7. 验证服务状态
curl http://localhost:8080/api/health
```

#### Docker 自动初始化流程

容器启动时会自动执行以下操作：

```
容器启动
    │
    ▼
检查 ~/.nanobot/config.json 是否存在
    │
    ├── 不存在 → 创建默认配置文件（空 API Key）
    │            创建 workspace/ 目录结构
    │            创建模板文件（MEMORY.md, SOUL.md 等）
    │
    └── 存在 → 跳过初始化
    │
    ▼
检查 API Key 是否已配置
    │
    ├── 已配置 → 显示 "[OK] API keys configured"
    │
    └── 未配置 → 显示警告和配置指引
    │
    ▼
启动 gateway 服务
```

#### 数据持久化

| 容器内路径                   | 宿主机路径               | 内容         |
| ---------------------------- | ------------------------ | ------------ |
| `/root/.nanobot/config.json` | `~/.nanobot/config.json` | 配置文件     |
| `/root/.nanobot/workspace/`  | `~/.nanobot/workspace/`  | 工作空间     |
| `/root/.nanobot/knowledge/`  | `~/.nanobot/knowledge/`  | 知识库索引   |
| `/root/.nanobot/cron/`       | `~/.nanobot/cron/`       | 定时任务数据 |

#### 常用 Docker 命令

```bash
# 查看容器状态
docker compose ps

# 查看日志
docker compose logs -f nanobot-gateway

# 重启服务
docker compose restart nanobot-gateway

# 停止服务
docker compose down

# 更新部署
git pull
docker compose build
docker compose up -d nanobot-gateway

# 进入容器调试
docker compose exec nanobot-gateway bash
```

### Linux Systemd 服务

```bash
# 创建服务文件
cat > ~/.config/systemd/user/nanobot-gateway.service << 'EOF'
[Unit]
Description=Nanobot Gateway
After=network.target

[Service]
Type=simple
ExecStart=%h/.local/bin/nanobot gateway
Restart=always
RestartSec=10
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=%h

[Install]
WantedBy=default.target
EOF

# 启用并启动
systemctl --user daemon-reload
systemctl --user enable --now nanobot-gateway

# 启用持久运行（退出登录后继续运行）
loginctl enable-linger $USER
```

### 生产环境建议

1. **资源配置**: 建议至少 1GB 内存，2 核 CPU
2. **日志管理**: 配置日志轮转，避免磁盘占满
3. **监控告警**: 配置健康检查和告警
4. **安全加固**:
   - 启用 `restrict_to_workspace`
   - 配置 `allow_from` 白名单
   - 使用 HTTPS 反向代理

---

## Windows 后台服务

项目提供了 Windows 后台服务管理脚本：

### 使用方式

**方式一：双击批处理文件**

- `start_nanobot.bat` - 启动后台服务
- `stop_nanobot.bat` - 停止后台服务

**方式二：PowerShell 脚本（推荐）**

```powershell
# 启动服务
.\nanobot-service.ps1 start

# 停止服务
.\nanobot-service.ps1 stop

# 重启服务
.\nanobot-service.ps1 restart

# 查看状态
.\nanobot-service.ps1 status
```

### 服务特性

- 后台运行，无控制台窗口
- 自动创建日志目录
- 服务状态检测
- 进程管理

---

## 注意事项

### 安全注意事项

1. **API Key 保护**
   - 不要将 API Key 提交到版本控制
   - 使用环境变量或配置文件存储
   - 定期轮换密钥

2. **Web UI 安全**
   - 启用 `web_ui.auth.enabled` 开启访问认证
   - 设置复杂且足够长的固定密码
   - 定期检查 `whitelist.json` 中的设备列表
   - 生产环境强烈建议启用认证

3. **渠道安全**
   - 配置 `allow_from` 白名单限制访问
   - WhatsApp Bridge Token 建议设置
   - 邮箱使用应用专用密码

4. **工具权限**
   - 生产环境启用 `restrict_to_workspace`
   - 谨慎使用 Shell 执行工具
   - MCP 服务器使用可信来源

### 性能优化

1. **内存管理**
   - 调整 `memory_window` 控制上下文大小
   - 定期清理旧会话
   - 启用记忆合并减少上下文

2. **响应速度**
   - 选择就近的 API 端点
   - 使用支持流式输出的模型
   - 减少不必要的工具调用

3. **资源限制**
   - Docker 部署配置资源限制
   - 监控内存和 CPU 使用
   - 合理设置并发连接数

### 常见问题

| 问题           | 解决方案                        |
| -------------- | ------------------------------- |
| API Key 无效   | 检查配置文件格式，确认 Key 有效 |
| 渠道无法连接   | 检查网络、Token、权限配置       |
| 响应超时       | 增加超时时间，检查网络连接      |
| 内存占用高     | 减小 memory_window，清理会话    |
| 工具执行失败   | 检查工作空间路径，确认权限      |
| 网络搜索不可用 | 配置博查搜索 API Key            |
| 天气查询不可用 | 配置心知天气 API Key            |

---

## 故障排除

### 日志查看

```bash
# CLI 模式显示日志
nanobot agent --logs

# Docker 日志
docker compose logs -f nanobot-gateway

# Systemd 日志
journalctl --user -u nanobot-gateway -f

# Windows 日志
type %USERPROFILE%\.nanobot\nanobot.log
```

### 常用诊断命令

```bash
# 检查配置
nanobot status

# 检查渠道状态
nanobot channels status

# 测试知识检索
nanobot knowledge search "测试查询"

# 手动运行定时任务
nanobot cron run <job_id>

# 测试 API 连接
curl http://localhost:8080/api/health
```

### 重置系统

```bash
# 重置配置（保留工作空间）
nanobot onboard

# 完全重置
rm -rf ~/.nanobot
nanobot onboard
```

---

## 安全说明

### API Key 管理

**重要**: 切勿将 API Key 提交到版本控制系统。

```bash
# ✅ 正确：存储在配置文件中并设置权限
chmod 600 ~/.nanobot/config.json

# ❌ 错误：将 Key 硬编码到代码中
```

**建议**:

- 将 API Key 存储在 `~/.nanobot/config.json` 中，并设置文件权限为 `0600`
- 生产环境考虑使用环境变量
- 定期轮换 API Key
- 开发环境和生产环境使用不同的 API Key

### 渠道访问控制

**重要**: 生产环境务必配置 `allowFrom` 列表。

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["123456789", "987654321"]
    }
  }
}
```

**说明**:

- `allowFrom` 列表为空时将**允许所有用户**访问
- Telegram 用户 ID 可通过 @userinfobot 获取

### Shell 命令执行

`exec` 工具可以执行 Shell 命令。系统已阻止危险命令模式，但仍需注意：

- ✅ 查看 agent 日志中的工具使用记录
- ✅ 理解 agent 运行的命令
- ✅ 使用有限权限的专用用户账户运行
- ✅ 切勿以 root 用户运行 AiMate

**已阻止的危险操作**:

- `rm -rf /` - 根文件系统删除
- Fork 炸弹
- 文件系统格式化 (`mkfs.*`)
- 其他破坏性操作

### 文件系统访问

文件操作有路径遍历保护，但建议：

- ✅ 使用专用用户账户运行 AiMate
- ✅ 使用文件系统权限保护敏感目录
- ✅ 定期审计日志中的文件操作

### 生产环境部署

1. **隔离环境**

   ```bash
   docker run --rm -it python:3.11
   pip install nanobot-ai
   ```

2. **使用专用用户**

   ```bash
   sudo useradd -m -s /bin/bash nanobot
   sudo -u nanobot nanobot gateway
   ```

3. **设置正确权限**

   ```bash
   chmod 700 ~/.nanobot
   chmod 600 ~/.nanobot/config.json
   ```

4. **定期更新依赖**
   ```bash
   pip install --upgrade nanobot-ai
   ```

### 安全特性

✅ **输入验证**

- 文件操作路径遍历保护
- 危险命令模式检测
- HTTP 请求输入长度限制

✅ **认证**

- 基于白名单的访问控制
- 认证失败日志记录

✅ **资源保护**

- 命令执行超时（默认 60 秒）
- 输出截断（10KB 限制）
- HTTP 请求超时（10-30 秒）

✅ **安全通信**

- 所有外部 API 调用默认使用 HTTPS
- TLS 加密 Telegram API
- WhatsApp bridge: 本地绑定 + 可选 Token 认证

### 安全检查清单

部署 AiMate 前请确认：

- [ ] API Key 安全存储（不在代码中）
- [ ] 配置文件权限设置为 0600
- [ ] 所有渠道配置了 `allowFrom` 列表
- [ ] 以非 root 用户运行
- [ ] 文件系统权限正确限制
- [ ] 依赖更新到最新安全版本
- [ ] 监控安全事件日志
- [ ] API 提供商配置了速率限制

---

## 附录

### CLI 命令参考

| 命令                       | 说明                 |
| -------------------------- | -------------------- |
| **基础命令**               |                      |
| `nanobot onboard`          | 初始化配置和工作空间 |
| `nanobot agent`            | 命令行聊天           |
| `nanobot gateway`          | 启动网关服务         |
| `nanobot status`           | 显示状态             |
| **渠道命令**               |                      |
| `nanobot channels status`  | 查看渠道状态         |
| `nanobot channels login`   | WhatsApp 扫码登录    |
| **定时任务命令**           |                      |
| `nanobot cron list`        | 列出定时任务         |
| `nanobot cron add`         | 添加定时任务         |
| `nanobot cron remove`      | 删除定时任务         |
| `nanobot cron enable`      | 启用/禁用定时任务    |
| `nanobot cron run`         | 手动执行定时任务     |
| **知识库命令**             |                      |
| `nanobot knowledge index`  | 索引笔记             |
| `nanobot knowledge search` | 搜索知识库           |
| `nanobot knowledge status` | 查看知识库状态       |
| `nanobot knowledge clear`  | 清除知识库索引       |
| **OAuth 登录命令**         |                      |
| `nanobot provider login`   | OAuth 提供商登录     |

### 支持的模型前缀

| 前缀               | 提供商           |
| ------------------ | ---------------- |
| `anthropic/`       | Anthropic Claude |
| `openai/`          | OpenAI GPT       |
| `openrouter/`      | OpenRouter       |
| `deepseek/`        | DeepSeek         |
| `gemini/`          | Google Gemini    |
| `dashscope/`       | 通义千问         |
| `moonshot/`        | Moonshot Kimi    |
| `zhipu/` 或 `zai/` | 智谱 GLM         |
| `minimax/`         | MiniMax          |
| `groq/`            | Groq             |

### 相关链接

- 官方仓库: https://github.com/HKUDS/nanobot
- 问题反馈: https://github.com/HKUDS/nanobot/issues
- Discord 社区: https://discord.gg/MnCvHqpUGB
- 博查搜索: https://bocha.ai
- 心知天气: https://www.seniverse.com

---

## 系统运行机制详解

### 核心启动流程

```
nanobot gateway
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 1. 加载配置 (config/loader.py)                                       │
│    - 读取 ~/.nanobot/config.json                                    │
│    - 解析环境变量覆盖                                                │
│    - 验证配置有效性                                                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. 创建 LLM Provider (providers/factory.py)                         │
│    - 根据模型前缀匹配提供商                                          │
│    - 设置 API Key 和 Base URL                                       │
│    - 初始化 LiteLLM 或自定义 Provider                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. 初始化 AgentLoop (agent/loop.py)                                  │
│    ├── 创建 MessageBus (消息路由)                                    │
│    ├── 创建 SessionManager (会话管理)                                │
│    ├── 初始化工具注册表 (ToolRegistry)                               │
│    │   - 文件操作: read_file, write_file, edit_file, list_dir      │
│    │   - Shell执行: exec                                            │
│    │   - 网络工具: web_search, web_fetch                            │
│    │   - 天气查询: weather, weather_forecast                        │
│    │   - 文档处理: docx_*, pdf_*, excel_*, pptx_*                   │
│    │   - 子Agent: spawn                                             │
│    │   - 文件返回: return_file                                      │
│    ├── 初始化子Agent系统                                             │
│    │   - 加载默认角色 (nanobot/config/roles.yaml)                   │
│    │   - 加载用户角色 (workspace/config/roles.yaml)                 │
│    │   - 创建 TaskManager, RoleManager, SubagentManager             │
│    └── 连接 MCP 服务器 (可选)                                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. 启动 Web UI (web/server.py)                                       │
│    ├── 创建 FastAPI 应用                                             │
│    ├── 配置认证中间件                                                │
│    ├── 注册 API 路由                                                 │
│    │   - /api/auth/*   认证接口                                      │
│    │   - /api/chat/*   聊天接口 (WebSocket)                          │
│    │   - /api/agents/* 子Agent管理                                   │
│    │   - /api/notes/*  笔记管理                                      │
│    │   - /api/skills/* 技能管理                                      │
│    │   - /api/upload/* 文件上传                                      │
│    └── 挂载静态文件                                                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. 并发运行服务                                                      │
│    ├── AgentLoop.run() - 消息处理主循环                              │
│    ├── WebServer - FastAPI 服务                                      │
│    ├── CronService - 定时任务 (可选)                                 │
│    └── HeartbeatService - 心跳服务 (可选)                            │
└─────────────────────────────────────────────────────────────────────┘
```

### 消息处理流程

```
用户发送消息
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ WebSocket 接收 (routes/chat.py)                                      │
│ - 解析消息内容                                                       │
│ - 处理附件文件                                                       │
│ - 构建 session_key = "web:{chat_id}"                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ AgentLoop.process_stream() (loop.py)                                 │
│                                                                      │
│ 1. 获取/创建会话                                                     │
│    session = sessions.get_or_create(session_key)                    │
│                                                                      │
│ 2. 构建上下文                                                        │
│    history = session.get_history(max_messages=memory_window)        │
│    messages = context.build_messages(                               │
│        history=history,                                             │
│        current_message=content,                                     │
│        media=attachments                                            │
│    )                                                                │
│                                                                      │
│ 3. 运行 Agent 循环                                                   │
│    while iteration < max_iterations:                                │
│        response = await provider.chat_stream(messages, tools)       │
│        if response.has_tool_calls:                                  │
│            执行工具调用                                              │
│            添加工具结果到消息                                        │
│        else:                                                        │
│            返回最终响应                                              │
│                                                                      │
│ 4. 保存会话                                                          │
│    _save_turn(session, messages, skip)                              │
│    sessions.save(session)                                           │
└─────────────────────────────────────────────────────────────────────┘
```

### 子Agent (Subagent) 系统架构

```
主Agent调用 spawn 工具
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ SpawnTool.execute() (tools/spawn.py)                                 │
│                                                                      │
│ 1. 匹配角色                                                          │
│    role = role_manager.match_role_for_task(task)                    │
│    或使用指定的 role 参数                                            │
│                                                                      │
│ 2. 创建任务                                                          │
│    task_obj = task_manager.create_task(...)                         │
│                                                                      │
│ 3. 打包上下文                                                        │
│    context_package = packer.pack_for_task(task, role, ...)          │
│                                                                      │
│ 4. 启动子Agent                                                       │
│    await subagent_manager.spawn_with_role(task, role, context)      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ SubagentManager.spawn_with_role() (subagent_manager.py)              │
│                                                                      │
│ 1. 获取角色定义                                                      │
│    role = role_manager.get_role(role_name)                          │
│                                                                      │
│ 2. 创建独立工作空间                                                  │
│    workspace = workspace/subagents/{task_id}/                       │
│                                                                      │
│ 3. 获取角色专用 Provider                                             │
│    provider, model = provider_factory.create_provider(role.config)  │
│                                                                      │
│ 4. 构建角色工具集                                                    │
│    tools = _build_tools_for_role(role, workspace)                   │
│    - 根据角色 capabilities.allowed_tools 过滤                        │
│                                                                      │
│ 5. 异步执行任务                                                      │
│    asyncio.create_task(_run_subagent(...))                          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ _run_subagent() 执行流程                                             │
│                                                                      │
│ 1. 构建系统提示                                                      │
│    system_prompt = _build_system_prompt(config)                     │
│    - 包含角色定义、工作空间、能力边界                                │
│                                                                      │
│ 2. 构建任务提示                                                      │
│    task_prompt = _build_task_prompt(config)                         │
│    - 包含任务描述、上下文、约束                                      │
│                                                                      │
│ 3. 执行 Agent 循环                                                   │
│    while iteration < max_iterations:                                │
│        response = await provider.chat(messages, tools)              │
│        执行工具调用...                                               │
│                                                                      │
│ 4. 收集产物                                                          │
│    artifacts = _collect_artifacts(workspace/output/)                │
│                                                                      │
│ 5. 汇报完成                                                          │
│    await _announce_completion(task, result)                         │
│    - 发送系统消息到主Agent                                           │
└─────────────────────────────────────────────────────────────────────┘
```

### 角色配置加载机制

```
AgentLoop._init_subagent_system()
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 1. 创建 RoleManager                                                  │
│    role_manager = RoleManager()                                     │
│    # 初始为空，无角色定义                                            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. 加载默认角色                                                      │
│    default_roles_path = Path(nanobot_config.__file__).parent /      │
│                         "roles.yaml"                                │
│    if default_roles_path.exists():                                  │
│        role_manager._load_from_yaml(default_roles_path)             │
│                                                                      │
│ 默认角色:                                                            │
│ - document_writer: 文档编写专家 📝                                   │
│ - code_developer: 代码开发专家 💻                                    │
│ - data_analyst: 数据分析专家 📊                                      │
│ - researcher: 研究分析专家 🔍                                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. 加载用户自定义角色 (可选)                                         │
│    user_roles_path = workspace / "config" / "roles.yaml"            │
│    if user_roles_path.exists():                                     │
│        role_manager._load_from_yaml(user_roles_path)                │
│    # 用户角色会覆盖同名默认角色                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 会话历史管理

```
SessionManager (session/manager.py)
    │
    ├── 存储位置: ~/.nanobot/sessions/
    │   文件格式: {channel}_{chat_id}.jsonl
    │
    ├── 内存缓存: LRU 缓存，最大 500 个会话
    │   TTL: 24 小时
    │
    └── 持久化格式 (JSONL):
        第一行: 元数据 {"_type": "metadata", "key": "...", ...}
        后续行: 消息 {"role": "user/assistant/tool", "content": "...", ...}
```

### 文件上传处理流程

```
用户上传文件
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 1. 上传到临时目录 (routes/upload.py)                                 │
│    - 验证文件类型和大小                                              │
│    - 保存到 upload_dir                                              │
│    - 返回文件路径                                                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. 构建文件提示 (context/builder.py)                                 │
│    _build_user_content(text, media=[file_path])                     │
│                                                                      │
│    根据文件扩展名添加工具使用提示:                                    │
│    - .doc → "使用 doc_read 工具读取"                                 │
│    - .docx → "使用 docx_read_text 工具读取"                          │
│    - .pdf → "使用 pdf_read_text 工具读取"                            │
│    - .xlsx → "使用 excel_read 工具读取"                              │
│    - .pptx → "使用 pptx_read 工具读取"                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. 模型调用相应工具读取文件                                          │
│    工具执行后返回文件内容                                            │
└─────────────────────────────────────────────────────────────────────┘
```

### 文件下载处理流程

```
模型调用 return_file 工具
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ReturnFileTool.execute() (tools/return_file.py)                      │
│                                                                      │
│ 返回格式:                                                            │
│ "FILE_RETURNED:{\"name\": \"xxx\", \"path\": \"xxx\", ...}"         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ AgentLoop._save_turn() 保存消息                                      │
│                                                                      │
│ 特殊处理: FILE_RETURNED 消息不截断                                   │
│ if content.startswith("FILE_RETURNED:"):                            │
│     pass  # 保持完整                                                 │
│ elif len(content) > _TOOL_RESULT_MAX_CHARS:                         │
│     entry["content"] = content[:2000] + "\n... (truncated)"         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 前端解析 (components.js)                                             │
│                                                                      │
│ 1. 解析 FILE_RETURNED 消息                                           │
│    if (content.startsWith("FILE_RETURNED:")) {                      │
│        const jsonStr = content.substring("FILE_RETURNED:".length);  │
│        const fileInfo = JSON.parse(jsonStr);                        │
│    }                                                                │
│                                                                      │
│ 2. 显示文件下载链接                                                  │
│    渲染为可点击的下载按钮                                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 已知问题与修复记录

### 问题 1: 子Agent角色未找到

**症状**: `spawn: 错误：未找到角色 'researcher'`

**原因**: `RoleManager` 初始化时未加载默认 `roles.yaml` 文件

**修复位置**: `nanobot/agent/loop.py` 的 `_init_subagent_system` 方法

**修复内容**:

```python
def _init_subagent_system(self, provider, workspace, bus, config):
    from nanobot.agent.roles.manager import RoleManager
    from nanobot import config as nanobot_config

    role_manager = RoleManager()

    # 加载默认角色
    default_roles_path = Path(nanobot_config.__file__).parent / "roles.yaml"
    if default_roles_path.exists():
        role_manager._load_from_yaml(default_roles_path)

    # 加载用户自定义角色
    user_roles_path = workspace / "config" / "roles.yaml"
    if user_roles_path.exists():
        role_manager._load_from_yaml(user_roles_path)
```

### 问题 2: 工具结果截断导致文件下载失败

**症状**: 页面刷新后文件下载链接消失

**原因**: `_TOOL_RESULT_MAX_CHARS = 500` 太小，`FILE_RETURNED` JSON 被截断

**修复位置**: `nanobot/agent/loop.py`

**修复内容**:

```python
_TOOL_RESULT_MAX_CHARS = 2000  # 从 500 增加到 2000

def _save_turn(self, session, messages, skip):
    for m in messages[skip:]:
        entry = {k: v for k, v in m.items() if k != "reasoning_content"}
        if entry.get("role") == "tool" and isinstance(entry.get("content"), str):
            content = entry["content"]
            if content.startswith("FILE_RETURNED:"):
                pass  # 不截断 FILE_RETURNED 消息
            elif len(content) > self._TOOL_RESULT_MAX_CHARS:
                entry["content"] = content[:self._TOOL_RESULT_MAX_CHARS] + "\n... (truncated)"
```

### 问题 3: 上传文件后模型不知道使用哪个工具

**症状**: 上传 .doc 文件后，模型尝试用 `read_file` 而非 `doc_read` 读取

**原因**: 文件提示信息不够具体，未指明应使用的工具

**修复位置**: `nanobot/agent/context/builder.py` 的 `_build_user_content` 方法

**修复内容**:

```python
if ext == ".doc":
    file_hints += f"- {name} (路径: {fpath}) → 使用 doc_read 工具读取\n"
elif ext == ".docx":
    file_hints += f"- {name} (路径: {fpath}) → 使用 docx_read_text 或 docx_read_structure 工具读取\n"
# ... 其他文件类型类似
```

### 问题 4: 前端无法解析文件下载信息

**症状**: 控制台报错 `JSON.parse` 失败

**原因**: 正则表达式 `/FILE_RETURNED:(\{[^}]+\})/` 无法匹配包含多个字段的对象

**修复位置**: `nanobot/web/static/js/components.js`

**修复内容**:

```javascript
// 旧代码 (有问题)
const match = content.match(/FILE_RETURNED:(\{[^}]+\})/);

// 新代码 (修复后)
if (content.startsWith("FILE_RETURNED:")) {
  const jsonStr = content.substring("FILE_RETURNED:".length);
  const fileInfo = JSON.parse(jsonStr);
}
```

### 问题 5: XML 工具调用标签未清理

**症状**: 某些模型的工具调用以 XML 格式嵌入内容，导致上下文污染

**原因**: `_sanitize_messages` 未清理 XML 格式的工具调用

**修复位置**: `nanobot/providers/litellm_provider.py`

**修复内容**:

```python
def _sanitize_messages(self, messages):
    for m in messages:
        if clean.get("role") == "assistant" and clean.get("tool_calls"):
            content = clean.get("content", "") or ""
            xml_pattern = r'<invoke\s+name="[^"]*"[^>]*>.*?</invoke>'
            content = re.sub(xml_pattern, "", content, flags=re.DOTALL)
            clean["content"] = content or None
```

### 问题 6: 文件名特殊字符导致 JSON 解析失败

**症状**: 文件名包含特殊字符（如双引号、换行符）时，前端无法解析 `FILE_RETURNED` 消息

**原因**: 使用字符串拼接生成 JSON，未正确转义特殊字符

**修复位置**: `nanobot/agent/tools/return_file.py`

**修复内容**:

```python
# 旧代码 (有问题)
return (
    f"FILE_RETURNED:{{\"file_id\": \"{file_id}\", "
    f"\"filename\": \"{dest_name}\", "
    f"\"original_name\": \"{display}\", "  # display 可能包含特殊字符
    f"\"file_type\": \"{self._get_file_type(ext)}\"}}"
)

# 新代码 (修复后)
file_info = {
    "file_id": file_id,
    "filename": dest_name,
    "original_name": display,
    "file_type": self._get_file_type(ext),
}
return f"FILE_RETURNED:{json.dumps(file_info, ensure_ascii=False)}"
```

同时添加了文件名安全处理：

```python
safe_display = "".join(c if c.isalnum() or c in "._-" else "_" for c in display)
```

---

## 开发者注意事项

### 1. 工具注册规范

工具类必须继承 `Tool` 基类，并正确实现 `name`, `description`, `parameters` 属性：

```python
class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "工具描述"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "参数描述"}
            },
            "required": ["param1"]
        }

    async def execute(self, param1: str, **kwargs) -> str:
        return "执行结果"
```

### 2. 角色配置格式

`roles.yaml` 文件格式：

```yaml
roles:
  document_writer:
    name: 文档编写专家
    description: 擅长编写各类技术文档
    icon: 📝
    enabled: true
    model_config:
      provider: deepseek
      model: deepseek/deepseek-chat
      temperature: 0.7
      max_tokens: 8192
    capabilities:
      allowed_tools:
        - read_file
        - write_file
        - edit_file
      forbidden_tools:
        - exec
    system_prompt: |
      你是一个专业的文档编写专家...
    max_iterations: 15
    timeout: 600
```

### 3. 会话消息格式

保存到 JSONL 文件的消息格式：

```json
{"_type": "metadata", "key": "web:default", "created_at": "2024-01-01T00:00:00", ...}
{"role": "user", "content": "你好", "timestamp": "2024-01-01T00:00:01"}
{"role": "assistant", "content": "你好！有什么可以帮助你的？", "timestamp": "2024-01-01T00:00:05"}
{"role": "tool", "tool_call_id": "xxx", "name": "read_file", "content": "文件内容..."}
```

### 4. FILE_RETURNED 协议

文件下载使用特殊协议：

```python
# 工具返回格式
return f"FILE_RETURNED:{json.dumps({
    'name': 'example.pdf',
    'path': '/path/to/file',
    'size': 1024,
    'mime_type': 'application/pdf'
})}"
```

前端解析：

```javascript
if (content.startsWith("FILE_RETURNED:")) {
  const fileInfo = JSON.parse(content.substring("FILE_RETURNED:".length));
  // 渲染下载链接
}
```

---

_本文档最后更新: 2026-03-14_

---

## 办公技能详细说明

### PDF 操作技能 (pdf-operations)

处理 PDF 文档的技能，支持以下工具：

| 工具                 | 功能                                    |
| -------------------- | --------------------------------------- |
| `pdf_read_text`      | 读取 PDF 文本内容                       |
| `pdf_read_structure` | 查看 PDF 结构信息（页数、尺寸、元数据） |
| `pdf_extract_images` | 提取 PDF 中的图片                       |
| `pdf_extract_tables` | 提取 PDF 中的表格数据                   |
| `pdf_to_markdown`    | 将 PDF 转换为 Markdown 格式             |

**安装依赖**：`pip install pymupdf`

**使用示例**：

```
用户: "帮我读取这个PDF的内容"
AI: [调用 pdf_read_text 工具]
```

### Excel 操作技能 (excel-operations)

处理 Excel 表格的技能，支持以下工具：

| 工具                 | 功能             |
| -------------------- | ---------------- |
| `excel_read`         | 读取 Excel 数据  |
| `excel_write`        | 写入数据到 Excel |
| `excel_list_sheets`  | 列出所有工作表   |
| `excel_create_sheet` | 创建新工作表     |
| `excel_set_cell`     | 设置单元格值     |

**安装依赖**：`pip install openpyxl`

### PowerPoint 操作技能 (pptx-operations)

处理演示文稿的技能，支持以下工具：

| 工具                  | 功能              |
| --------------------- | ----------------- |
| `pptx_read`           | 读取 PPT 内容     |
| `pptx_create`         | 创建新 PPT        |
| `pptx_add_slide`      | 添加幻灯片        |
| `pptx_extract_images` | 提取 PPT 中的图片 |
| `pptx_list_slides`    | 列出幻灯片        |

**安装依赖**：`pip install python-pptx`

### OCR 文字识别技能 (ocr-operations)

识别图片中文字的技能，支持以下工具：

| 工具            | 功能                 |
| --------------- | -------------------- |
| `ocr_recognize` | 识别单张图片中的文字 |
| `ocr_batch`     | 批量识别目录中的图片 |
| `ocr_pdf`       | 对 PDF 进行 OCR 识别 |

**安装依赖**：`pip install rapidocr-onnxruntime`

**支持的图片格式**：PNG、JPG、JPEG、BMP、GIF、TIFF、WebP
