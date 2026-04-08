# AiMate Docker 部署指南

> **版本**: 0.1.4.post2
> **更新时间**: 2026-03-31
> **知识库支持**: ✅ 已包含（chromadb, sentence-transformers, jieba）

---

## 目录

- [一、项目概述](#一项目概述)
- [二、环境要求](#二环境要求)
- [三、数据目录结构](#三数据目录结构)
- [四、单机部署（单实例）](#四单机部署单实例)
- [五、知识库配置](#五知识库配置)
- [六、多实例部署](#六多实例部署)
- [七、配置详解](#七配置详解)
- [八、服务管理命令](#八服务管理命令)
- [九、故障排除](#九故障排除)

---

## 一、项目概述

AiMate 是一个超轻量级的个人 AI 助手框架，核心特性：

| 特性     | 说明                                                       |
| -------- | ---------------------------------------------------------- |
| 多渠道   | 支持 Telegram、Discord、WhatsApp、飞书、Slack、QQ 等       |
| 多模型   | 支持 OpenRouter、Anthropic、OpenAI、DeepSeek 等 20+ 提供商 |
| 工具调用 | 内置文件操作、Shell 执行、网络搜索、天气查询等工具         |
| 记忆系统 | 双层记忆架构（长期记忆 + 历史日志）                        |
| 知识检索 | 混合检索（BM25 + 向量 + 知识图谱）                         |
| Web UI   | FastAPI + Vue 3 现代化界面                                 |

### Docker 暴露的端口

| 端口  | 服务        | 说明         |
| ----- | ----------- | ------------ |
| 8080  | Web UI      | 用户界面访问 |
| 18790 | Gateway API | 程序化接口   |

---

## 二、环境要求

### 2.1 系统要求

| 项目           | 要求                       |
| -------------- | -------------------------- |
| Docker         | 20.10+                     |
| Docker Compose | 2.0+                       |
| 内存           | 最少 512MB，推荐 2GB       |
| CPU            | 最少 0.5 核心，推荐 2 核心 |

### 2.2 验证 Docker 环境

```powershell
# 检查 Docker 版本
docker --version

# 检查 Docker Compose 版本
docker compose version

# 验证 Docker 运行状态
docker info
```

---

## 三、数据目录结构

每个实例的数据持久化在宿主机的 `~/.nanobot` 目录（可通过 volumes 映射自定义）：

```
~/.nanobot/
├── config.json          # 主配置文件（API密钥、模型配置等）
├── whitelist.json       # Web UI 认证白名单（可选）
├── workspace/           # 工作空间
│   ├── memory/          # 记忆文件
│   │   ├── MEMORY.md    # 长期记忆
│   │   └── HISTORY.md   # 历史记录
│   ├── SOUL.md          # AI 人格定义
│   ├── AGENTS.md        # Agent 配置
│   ├── TOOLS.md         # 工具配置
│   ├── HEARTBEAT.md     # 心跳配置
│   ├── daily/           # 日记目录
│   ├── projects/        # 项目笔记目录
│   ├── topics/          # 主题笔记目录
│   └── uploads/         # 上传文件目录
├── knowledge/           # 知识库向量索引
└── cron/                # 定时任务数据
```

**重要**：配置文件和数据分离，升级镜像不会丢失数据。

---

## 四、单机部署（单实例）

### 4.1 方式一：从头创建（推荐首次部署）

#### 步骤 1：创建数据目录

```powershell
# Windows
mkdir -p ~/.nanobot

# Linux / macOS
mkdir -p ~/.nanobot
```

#### 步骤 2：创建配置文件

手动创建 `~/.nanobot/config.json`，填入你的 API Key：

```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.nanobot/workspace",
      "model": "anthropic/claude-sonnet-4-20250514",
      "max_tokens": 8192,
      "temperature": 0.1,
      "max_tool_iterations": 40,
      "memory_window": 100
    }
  },
  "providers": {
    "anthropic": {
      "api_key": "sk-ant-your-anthropic-key-here"
    },
    "deepseek": {
      "api_key": "sk-your-deepseek-key-here"
    },
    "openai": {
      "api_key": "sk-your-openai-key-here"
    },
    "openrouter": {
      "api_key": "sk-your-openrouter-key-here"
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
        "enabled": true,
        "password": "your-web-ui-password"
      }
    }
  },
  "channels": {
    "send_progress": true
  }
}
```

#### 步骤 3：构建并启动

```powershell
# 进入项目目录
cd d:\program\nanobot-0.1.4.post2

# 构建并启动（单实例直接使用 docker-compose.yml）
docker compose up -d --build nanobot-gateway
```

#### 步骤 4：验证服务

```powershell
# 检查容器状态
docker ps --filter "name=nanobot-gateway"

# 查看启动日志
docker logs nanobot-gateway

# 健康检查
# 浏览器访问 http://localhost:8080/api/health
```

### 4.2 方式二：自动初始化（容器首次启动时自动创建配置）

如果宿主机 `~/.nanobot/config.json` 不存在，容器启动时会自动创建默认配置。

```powershell
# 只需创建空目录
mkdir -p ~/.nanobot

# 启动容器
docker compose up -d --build nanobot-gateway

# 容器会自动创建默认配置，然后你可以通过 Web UI 配置 API Key
```

---

## 五、知识库配置

### 5.1 知识库功能说明

知识库功能支持：

- **向量检索**：基于 embedding 模型进行语义搜索
- **BM25 检索**：基于关键词的文本检索
- **混合检索**：结合向量和 BM25 的混合搜索（RRF 算法）
- **自动索引**：自动为笔记目录建立索引
- **中文分词**：使用 jieba 进行中文分词

### 5.2 两种部署模式

| 模式            | Embedding 方式               | 镜像大小 | 内存需求 | 推荐场景                   |
| --------------- | ---------------------------- | -------- | -------- | -------------------------- |
| **内置模式**    | sentence-transformers (本地) | ~6.5GB   | 高       | 有充足资源                 |
| **Ollama 模式** | Ollama API (外部)            | ~1.5GB   | 低       | 2GB 内存服务器、多实例部署 |

### 5.3 Ollama 模式（推荐）

Ollama 模式将 embedding 计算外置到独立的 Ollama 服务，显著减小 nanobot 镜像体积。

#### 架构图

```
┌──────────────────────────────────────────────────────────┐
│                    Docker Network                         │
│                                                          │
│  ┌─────────────────────┐    ┌─────────────────────────┐  │
│  │ nanobot-gateway     │    │      ollama             │  │
│  │      (~1.5GB)       │───▶│   (~500MB)             │  │
│  │  - ChromaDB         │    │  - nomic-embed-text    │  │
│  │  - rank-bm25       │    │    (~274MB)            │  │
│  │  - jieba           │    │                         │  │
│  └─────────────────────┘    └─────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

#### 空间节省

| 模式        | nanobot 镜像 | Ollama | 总计      |
| ----------- | ------------ | ------ | --------- |
| 内置模式    | 6.5GB        | 0      | 6.5GB     |
| Ollama 模式 | 1.5GB        | 0.8GB  | 2.3GB     |
| **节省**    | **5GB**      | -      | **4.2GB** |

### 5.4 配置 Ollama 模式

#### 环境变量

```bash
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

#### config.json 配置

```json
{
  "tools": {
    "knowledge": {
      "index": {
        "enabled": true,
        "embedding_model": "nomic-embed-text",
        "use_ollama": true,
        "ollama_base_url": "http://localhost:11434",
        "use_bm25": true,
        "use_vector": true
      }
    }
  }
}
```

### 5.5 Ollama Embedding 模型推荐

| 模型                     | 大小   | 中文支持 | MTEB 得分 | 推荐        |
| ------------------------ | ------ | -------- | --------- | ----------- |
| `nomic-embed-text`       | ~274MB | ✅ 良好  | ~62       | ⭐ **首选** |
| `snowflake-arctic-embed` | ~167MB | ✅ 良好  | ~60       | 备用        |
| `bge-m3`                 | ~1.2GB | ✅ 优秀  | ~65       | 精度优先    |

**推荐 `nomic-embed-text`**，因为：

- 中文支持良好
- 体积小，内存占用低
- Ollama 官方优化，运行稳定

### 5.6 通用配置（内置/Ollama 通用）

编辑 `~/.nanobot/config.json`，启用知识库：

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

### 5.7 配置参数说明

| 参数               | 说明             | 默认值                                       |
| ------------------ | ---------------- | -------------------------------------------- |
| `enabled`          | 是否启用知识库   | `false`                                      |
| `embedding_model`  | Embedding 模型   | `BAAI/bge-small-zh-v1.5`                     |
| `persist_dir`      | 索引持久化目录   | `~/.nanobot/knowledge`                       |
| `chunk_size`       | 文档分块大小     | `512`                                        |
| `chunk_overlap`    | 分块重叠大小     | `50`                                         |
| `use_bm25`         | 是否启用 BM25    | `true`                                       |
| `use_vector`       | 是否启用向量检索 | `true`                                       |
| `rrf_k`            | RRF 算法参数     | `60`                                         |
| `auto_index_notes` | 是否自动索引笔记 | `true`                                       |
| `notes_dirs`       | 笔记目录列表     | `["daily", "projects", "topics", "pending"]` |

### 5.8 常用 Embedding 模型

| 模型                                     | 说明             | 内存需求 |
| ---------------------------------------- | ---------------- | -------- |
| `BAAI/bge-small-zh-v1.5`                 | 中文小模型，推荐 | ~500MB   |
| `BAAI/bge-base-zh-v1.5`                  | 中文中模型       | ~1.5GB   |
| `sentence-transformers/all-MiniLM-L6-v2` | 英文模型         | ~500MB   |

### 5.9 笔记目录结构

知识库会自动索引以下笔记目录：

```
~/.nanobot/workspace/
├── daily/       # 日记笔记
├── projects/    # 项目笔记
├── personal/    # 个人笔记
├── topics/      # 主题笔记
└── pending/     # 待办笔记
```

每个目录下的 `.md` 文件会被自动索引。

---

## 六、轻量级多实例部署（2GB RAM）

适用于内存受限的服务器（2GB RAM），部署 2 个 nanobot 实例共用 1 个 ollama 服务。

### 6.1 内存分配

| 服务            | 内存限制 | 实例数 | 总计     |
| --------------- | -------- | ------ | -------- |
| nanobot-gateway | 256MB    | 2      | 512MB    |
| ollama          | 512MB    | 1      | 512MB    |
| 系统预留        | ~1GB     | -      | 1GB      |
| **总计**        |          |        | **~2GB** |

### 6.2 端口规划

| 服务          | 端口  | 说明          |
| ------------- | ----- | ------------- |
| nanobot-user1 | 8081  | Web UI        |
| nanobot-user1 | 18791 | API           |
| nanobot-user2 | 8082  | Web UI        |
| nanobot-user2 | 18792 | API           |
| ollama        | 11434 | Embedding API |

### 6.3 部署步骤

```powershell
# 1. 创建用户数据目录
mkdir -p ~/.nanobot-user1
mkdir -p ~/.nanobot-user2

# 2. 配置文件（参考上方 config.json）
# 编辑 ~/.nanobot-user1/config.json
# 编辑 ~/.nanobot-user2/config.json

# 3. 构建并启动
docker compose -f docker-compose.mini.yml up -d

# 4. 首次启动后，手动拉取 ollama 模型（如果未自动拉取）
docker exec nanobot-ollama ollama pull nomic-embed-text

# 5. 验证服务
docker compose -f docker-compose.mini.yml ps
```

### 6.4 访问服务

| 实例  | Web UI                | API                    |
| ----- | --------------------- | ---------------------- |
| user1 | http://localhost:8081 | http://localhost:18791 |
| user2 | http://localhost:8082 | http://localhost:18792 |

### 6.5 停止服务

```powershell
docker compose -f docker-compose.mini.yml down
```

---

## 七、多实例部署（标准）

在同一服务器上部署多个 nanobot 实例，实现多用户隔离或功能隔离。

### 6.1 核心原理

每个实例需要：

| 配置项           | 说明         | 多实例时要求                 |
| ---------------- | ------------ | ---------------------------- |
| `volumes`        | 数据目录映射 | 每个实例映射到不同宿主机目录 |
| `ports`          | 服务端口     | 每个实例使用不同端口         |
| `container_name` | 容器名称     | 必须唯一                     |

### 6.2 创建多实例配置文件

创建 `docker-compose.multi.yml`：

```yaml
# docker-compose.multi.yml

x-common-config: &common-config
  build:
    context: .
    dockerfile: Dockerfile
  restart: unless-stopped
  networks:
    - nanobot-network

services:
  # ============ 实例 1：用户 A ============
  nanobot-user1:
    <<: *common-config
    container_name: nanobot-user1
    volumes:
      - ~/.nanobot-user1:/root/.nanobot
    ports:
      - "18080:8080"
      - "18791:18790"
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 2G

  # ============ 实例 2：用户 B ============
  nanobot-user2:
    <<: *common-config
    container_name: nanobot-user2
    volumes:
      - ~/.nanobot-user2:/root/.nanobot
    ports:
      - "18081:8080"
      - "18792:18790"
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 2G

  # ============ 实例 3：测试环境 ============
  nanobot-test:
    <<: *common-config
    container_name: nanobot-test
    volumes:
      - ~/.nanobot-test:/root/.nanobot
    ports:
      - "18082:8080"
      - "18793:18790"
    deploy:
      resources:
        limits:
          cpus: "1"
          memory: 1G

networks:
  nanobot-network:
    driver: bridge
```

### 5.3 为每个实例创建配置目录和文件

```powershell
# 实例 1
mkdir -p ~/.nanobot-user1
# 编辑 ~/.nanobot-user1/config.json，填入用户 A 的 API Key

# 实例 2
mkdir -p ~/.nanobot-user2
# 编辑 ~/.nanobot-user2/config.json，填入用户 B 的 API Key

# 实例 3
mkdir -p ~/.nanobot-test
# 编辑 ~/.nanobot-test/config.json，填入测试用的 API Key
```

### 6.4 启动多实例

```powershell
# 构建并启动所有实例
docker compose -f docker-compose.multi.yml up -d --build

# 只启动特定实例
docker compose -f docker-compose.multi.yml up -d --build nanobot-user1
```

### 5.5 端口规划表

| 实例 | 容器名          | Web UI | API   | 数据目录           |
| ---- | --------------- | ------ | ----- | ------------------ |
| 1    | `nanobot-user1` | 18080  | 18791 | `~/.nanobot-user1` |
| 2    | `nanobot-user2` | 18081  | 18792 | `~/.nanobot-user2` |
| 3    | `nanobot-test`  | 18082  | 18793 | `~/.nanobot-test`  |

---

## 七、配置详解

### 8.1 config.json 完整结构

```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.nanobot/workspace",
      "model": "anthropic/claude-sonnet-4-20250514",
      "max_tokens": 8192,
      "temperature": 0.1,
      "max_tool_iterations": 40,
      "memory_window": 100
    }
  },
  "providers": {
    "custom": { "api_key": "" },
    "anthropic": { "api_key": "sk-ant-xxx" },
    "openai": { "api_key": "sk-xxx" },
    "openrouter": { "api_key": "sk-xxx" },
    "deepseek": { "api_key": "sk-xxx" },
    "groq": { "api_key": "" },
    "zhipu": { "api_key": "" },
    "dashscope": { "api_key": "" },
    "gemini": { "api_key": "" },
    "siliconflow": { "api_key": "" }
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
        "enabled": true,
        "password": "your-password"
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
    "discord": {
      "enabled": false,
      "token": "",
      "allow_from": []
    }
  },
  "tools": {
    "web": {
      "search": {
        "api_key": "",
        "max_results": 10
      }
    },
    "exec": {
      "timeout": 60
    },
    "restrict_to_workspace": false
  }
}
```

### 6.2 支持的模型提供商

| Provider    | 示例 Model                                               |
| ----------- | -------------------------------------------------------- |
| Anthropic   | `anthropic/claude-opus-4-5`, `anthropic/claude-sonnet-4` |
| OpenAI      | `openai/gpt-4-turbo`, `openai/gpt-3.5-turbo`             |
| DeepSeek    | `deepseek/deepseek-chat`, `deepseek/deepseek-coder`      |
| OpenRouter  | `openrouter/anthropic/claude-3-opus`                     |
| SiliconFlow | `siliconflow/openai/gpt-4`                               |
| Groq        | `groq/llama-3.1-70b-versatile`                           |

### 6.3 工作空间文件说明

| 文件           | 作用                               |
| -------------- | ---------------------------------- |
| `SOUL.md`      | 定义 AI 人格、性格、行为准则       |
| `MEMORY.md`    | 长期记忆，存储重要的用户偏好和信息 |
| `HISTORY.md`   | 对话历史摘要                       |
| `AGENTS.md`    | 子 Agent 系统配置                  |
| `TOOLS.md`     | 工具使用说明和配置                 |
| `HEARTBEAT.md` | 心跳/定时任务配置                  |

---

## 八、服务管理命令

### 8.1 基础命令

```powershell
# 查看运行中的容器
docker ps --filter "name=nanobot"

# 查看所有容器（包括已停止）
docker ps -a --filter "name=nanobot"

# 启动服务
docker compose up -d nanobot-gateway

# 停止服务
docker compose down

# 重启服务
docker compose restart nanobot-gateway
```

### 7.2 日志管理

```powershell
# 查看实时日志
docker logs -f nanobot-gateway

# 查看最近 100 行日志
docker logs nanobot-gateway --tail 100

# 查看错误日志
docker logs nanobot-gateway 2>&1 | Select-String -Pattern "ERROR"
```

### 9.3 多实例管理

```powershell
# 启动特定实例
docker start nanobot-user1

# 停止特定实例
docker stop nanobot-user1

# 重启特定实例
docker restart nanobot-user1

# 查看特定实例日志
docker logs -f nanobot-user1

# 删除特定实例（不会删除数据）
docker rm nanobot-user1
```

### 7.4 进入容器调试

```powershell
# 进入容器 bash
docker exec -it nanobot-gateway /bin/bash

# 或者用 sh
docker exec -it nanobot-gateway /bin/sh
```

### 9.5 镜像管理

```powershell
# 重新构建镜像
docker compose build nanobot-gateway

# 查看本地镜像
docker images | Select-String "nanobot"

# 删除旧镜像（谨慎操作）
docker rmi nanobot-014post2-nanobot-gateway
```

---

## 十、故障排除

### 8.1 常见问题

#### Q1: 容器健康检查失败

```powershell
# 查看详细日志
docker logs nanobot-gateway

# 检查端口是否被占用
netstat -ano | findstr "8080"
netstat -ano | findstr "18790"
```

#### Q2: API Key 无效或未生效

1. 确认 `config.json` 中 `providers` 下的 `api_key` 已正确填写
2. 重启容器使配置生效：
   ```powershell
   docker compose restart nanobot-gateway
   ```
3. 通过 Web UI 验证配置是否正确加载

#### Q3: Web UI 无法访问

1. 检查容器是否运行：
   ```powershell
   docker ps --filter "name=nanobot-gateway"
   ```
2. 检查端口映射：
   ```powershell
   docker port nanobot-gateway
   ```
3. 检查防火墙设置

#### Q4: 权限问题

```powershell
# Windows - 确保目录可读写
icacls $env:USERPROFILE\.nanobot /grant Everyone:F /T

# Linux/macOS
chmod -R 755 ~/.nanobot
```

### 10.2 完整重装步骤

如果需要完全重新部署：

```powershell
# 1. 停止并删除容器
docker compose down

# 2. 删除镜像（可选，清理空间）
docker rmi nanobot-014post2-nanobot-gateway

# 3. 重新构建并启动
docker compose up -d --build nanobot-gateway

# 4. 验证服务
docker ps --filter "name=nanobot-gateway"
docker logs nanobot-gateway --tail 50
```

### 10.3 性能调优

根据服务器资源调整 `docker-compose.yml` 中的资源限制：

```yaml
deploy:
  resources:
    limits:
      cpus: "2" # 限制 CPU 使用
      memory: 2G # 限制内存使用
    reservations:
      cpus: "0.5" # 保留 CPU
      memory: 512M # 保留内存
```

---

## 附录：环境变量参考

虽然推荐使用配置文件管理 API Key，但也支持环境变量方式：

| 变量名                       | 说明               |
| ---------------------------- | ------------------ |
| `NANOBOT_DEEPSEEK_API_KEY`   | DeepSeek API Key   |
| `NANOBOT_OPENAI_API_KEY`     | OpenAI API Key     |
| `NANOBOT_ANTHROPIC_API_KEY`  | Anthropic API Key  |
| `NANOBOT_OPENROUTER_API_KEY` | OpenRouter API Key |
| `NANOBOT_WEB_PASSWORD`       | Web UI 访问密码    |
| `NANOBOT_PERSISTENCE_SECRET` | 数据持久化签名密钥 |

---

_文档结束_
