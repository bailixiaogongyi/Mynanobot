# nanobot 功能扩展方案

> **版本说明**：本方案基于已实现的混合检索记忆系统，规划 Web 界面开发、技能系统扩展等后续功能。

---

## 一、项目现状分析

### 1.1 现有架构

```
nanobot/
├── agent/                    # 核心代理模块
│   ├── memory.py             # 记忆存储（MEMORY.md + HISTORY.md）
│   ├── context.py            # 上下文构建器
│   ├── skills.py             # 技能加载器
│   └── tools/                # 工具集
│       └── note_search.py    # 笔记搜索工具（已实现）
├── channels/                 # 通信渠道（Telegram, WhatsApp 等）
├── cli/                      # 命令行接口
├── config/                   # 配置管理
│   └── schema.py             # 已扩展 KnowledgeConfig
├── knowledge/                # 知识检索模块（已实现）
│   ├── hybrid_retriever.py   # 混合检索器
│   ├── note_processor.py     # 笔记处理器
│   ├── bm25_persist.py       # BM25 持久化
│   ├── incremental_indexer.py# 增量索引器
│   └── cache.py              # 查询缓存
├── providers/                # LLM 提供商
├── session/                  # 会话管理
├── skills/                   # 内置技能
└── templates/                # 模板文件
```

### 1.2 已实现的记忆系统

| 组件         | 文件                               | 功能                           | 状态      |
| ------------ | ---------------------------------- | ------------------------------ | --------- |
| 混合检索器   | `knowledge/hybrid_retriever.py`    | BM25 + 向量检索 + RRF 融合     | ✅ 已实现 |
| 笔记处理器   | `knowledge/note_processor.py`      | Markdown 解析与智能分块        | ✅ 已实现 |
| BM25 持久化  | `knowledge/bm25_persist.py`        | BM25 索引存储与加载            | ✅ 已实现 |
| 增量索引器   | `knowledge/incremental_indexer.py` | 文件变更追踪                   | ✅ 已实现 |
| 查询缓存     | `knowledge/cache.py`               | LRU 缓存 + TTL                 | ✅ 已实现 |
| 笔记搜索工具 | `agent/tools/note_search.py`       | NoteSearchTool + NoteIndexTool | ✅ 已实现 |
| 配置扩展     | `config/schema.py`                 | KnowledgeConfig                | ✅ 已实现 |

### 1.3 技术选型（已确定）

| 维度     | 选择              | 说明                  |
| -------- | ----------------- | --------------------- |
| 向量存储 | ChromaDB          | HNSW 索引，QPS 15,800 |
| 嵌入模型 | bge-small-zh-v1.5 | ~400MB，中文支持优秀  |
| 检索策略 | BM25 + 向量 + RRF | 混合检索，召回率高    |
| 内存占用 | ~500MB            | 符合轻量化要求        |

---

## 二、待开发功能

### 2.1 Web 界面模块

**目标**：提供图形化操作界面，降低使用门槛。

| 功能     | 优先级 | 说明                   |
| -------- | ------ | ---------------------- |
| 对话管理 | 高     | 多会话对话、历史记录   |
| 笔记管理 | 高     | 文件树、编辑器、搜索   |
| 技能查看 | 中     | 技能列表、详情展示     |
| 配置管理 | 中     | 模型切换、API Key 配置 |

### 2.2 技能系统扩展

**目标**：增强笔记管理能力。

| 技能        | 优先级 | 说明                       |
| ----------- | ------ | -------------------------- |
| daily-note  | 高     | 自动创建每日笔记           |
| archive     | 中     | 归档旧笔记                 |
| note-search | 高     | 已通过 NoteSearchTool 实现 |

---

## 三、Web 界面模块设计

### 3.1 技术选型

| 组件     | 技术选型     | 理由                       |
| -------- | ------------ | -------------------------- |
| 后端框架 | FastAPI      | 与现有项目一致，异步支持好 |
| 前端框架 | Vue 3        | 轻量、响应式、组件化       |
| UI 组件  | Element Plus | 中文友好、组件丰富         |
| 样式方案 | TailwindCSS  | 响应式设计、自适应         |

### 3.2 依赖清单

```toml
[project.optional-dependencies]
web-ui = [
    "fastapi>=0.115.0,<1.0.0",
    "uvicorn>=0.32.0,<1.0.0",
    "python-multipart>=0.0.18,<1.0.0",
]
```

### 3.3 目录结构规划

```
nanobot/
├── web/                        # 新增：Web 界面模块
│   ├── __init__.py
│   ├── server.py               # FastAPI 服务入口
│   ├── routes/                 # API 路由
│   │   ├── __init__.py
│   │   ├── chat.py             # 对话 API
│   │   ├── notes.py            # 笔记 API
│   │   ├── skills.py           # 技能 API
│   │   └── config.py           # 配置 API
│   ├── static/                 # 静态资源（Vue 编译后）
│   └── templates/              # HTML 模板

custom/                         # 自定义扩展目录
├── web-frontend/               # Vue 前端源码
│   ├── src/
│   │   ├── views/              # 页面组件
│   │   ├── components/         # 通用组件
│   │   ├── stores/             # 状态管理
│   │   └── api/                # API 调用
│   ├── package.json
│   └── vite.config.ts
```

### 3.4 API 设计

#### 3.4.1 对话 API (web/routes/chat.py)

> **安全说明**：Web UI 只能访问 `web:xxx` 格式的会话，不允许访问其他频道的会话。

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class ChatMessage(BaseModel):
    content: str
    chat_id: Optional[str] = "default"  # 会话 ID，如 "default", "project-a"

class ChatResponse(BaseModel):
    content: str
    role: str = "assistant"

@router.post("/send", response_model=ChatResponse)
async def send_message(message: ChatMessage):
    """发送消息并获取响应

    session_key 自动构建为 "web:{chat_id}"
    """
    pass

@router.websocket("/ws/{chat_id}")
async def websocket_chat(websocket: WebSocket, chat_id: str):
    """WebSocket 实时对话

    session_key 自动构建为 "web:{chat_id}"
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            response = await process_message(data, chat_id)
            await websocket.send_text(response)
    except WebSocketDisconnect:
        pass

@router.get("/sessions")
async def list_sessions():
    """列出 Web 频道下的所有会话"""
    pass

@router.post("/sessions")
async def create_session(name: str):
    """创建新会话

    session_key 自动构建为 "web:{name}"
    """
    pass

@router.delete("/sessions/{chat_id}")
async def delete_session(chat_id: str):
    """删除会话"""
    pass
```

#### 3.4.2 笔记 API (web/routes/notes.py)

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

router = APIRouter()

class NoteInfo(BaseModel):
    path: str
    name: str
    type: str
    size: int
    modified_at: str

class NoteContent(BaseModel):
    path: str
    content: str

@router.get("/list")
async def list_notes(directory: Optional[str] = None):
    """列出笔记目录"""
    pass

@router.get("/read")
async def read_note(path: str):
    """读取笔记内容"""
    pass

@router.post("/save")
async def save_note(note: NoteContent):
    """保存笔记内容"""
    pass

@router.get("/search")
async def search_notes(q: str, top_k: int = 5):
    """搜索笔记（语义检索）- 使用已实现的 HybridRetriever"""
    pass

@router.post("/index")
async def index_notes(directory: str):
    """索引指定目录的笔记"""
    pass
```

#### 3.4.3 技能 API (web/routes/skills.py)

```python
from fastapi import APIRouter
from typing import Optional

router = APIRouter()

@router.get("/list")
async def list_skills(source: Optional[str] = None):
    """列出所有技能"""
    pass

@router.get("/{skill_name}")
async def get_skill(skill_name: str):
    """获取技能详情"""
    pass
```

#### 3.4.4 配置 API (web/routes/config.py)

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

@router.get("/")
async def get_config():
    """获取当前配置"""
    pass

@router.post("/model")
async def set_model(model: str):
    """切换模型"""
    pass

@router.post("/provider/{provider_name}")
async def set_provider_api_key(provider_name: str, api_key: str):
    """设置提供商 API Key"""
    pass
```

### 3.5 前端界面设计

#### 3.5.1 页面结构

```
┌─────────────────────────────────────────────────────────────────────────┐
│  nanobot                                    [对话] [笔记] [技能] [配置]   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │                        主内容区域                                  │  │
│  │                                                                   │  │
│  │   - 对话页面：聊天界面 + 会话列表（Web 频道专属）                  │  │
│  │   - 笔记页面：文件树 + 编辑器 + 语义搜索                          │  │
│  │   - 技能页面：技能卡片列表 + 详情弹窗（只读）                      │  │
│  │   - 配置页面：模型/知识检索/渠道配置（敏感信息脱敏）               │  │
│  │                                                                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 3.5.2 对话页面设计

> **说明**：Web UI 是 Web 频道的专属客户端，只能访问 `web:xxx` 格式的会话。
> 左侧列表展示的是 Web 频道下的会话，而非其他通信渠道（Telegram、Feishu 等）。

```
┌─────────────────────────────────────────────────────────────────────────┐
│  对话                                                                   │
├────────────────┬────────────────────────────────────────────────────────┤
│                │                                                        │
│   会话列表      │                    对话区域                            │
│   (web:xxx)    │                                                        │
│                │   ┌──────────────────────────────────────────────────┐│
│   ┌──────────┐ │   │ User: 帮我整理今天的笔记                         ││
│   │ 默认对话  │ │   │                                                  ││
│   └──────────┘ │   │ Assistant: 好的，我来帮你整理...                  ││
│   ┌──────────┐ │   │                                                  ││
│   │ 项目 A   │ │   └──────────────────────────────────────────────────┘│
│   └──────────┘ │                                                        │
│   ┌──────────┐ │   ┌──────────────────────────────────────────────────┐│
│   │ 学习笔记  │ │   │ [输入消息...]                          [发送]     ││
│   └──────────┘ │   └──────────────────────────────────────────────────┘│
│                │                                                        │
│   [+ 新建会话] │                                                        │
│                │                                                        │
└────────────────┴────────────────────────────────────────────────────────┘

会话示例：
- 默认对话  → session_key: "web:default"
- 项目 A    → session_key: "web:project-a"
- 学习笔记  → session_key: "web:study"
```

#### 3.5.3 笔记页面设计

> **说明**：笔记页面展示工作空间中的笔记文件，支持浏览、编辑和语义搜索。

```
┌─────────────────────────────────────────────────────────────────────────┐
│  笔记                                    [搜索: ___________] [索引]      │
├────────────────┬────────────────────────────────────────────────────────┤
│                │                                                        │
│   目录树        │                    编辑器                              │
│                │                                                        │
│   📁 daily     │   # 2026-02-28                                        │
│   📁 projects  │                                                        │
│     └─ 📄 项目A│   ## 今日任务                                          │
│     └─ 📄 项目B│   - 完成记忆系统升级方案                                │
│   📁 personal  │   - 编写 Web 界面代码                                   │
│   📁 topics    │                                                        │
│   📁 pending   │   ## 笔记                                              │
│   📁 memory    │   - bge-small-zh-v1.5 内存占用约 400MB                 │
│     └─ 📄 02-22│                                                        │
│     └─ 📄 02-23│                                                        │
│                │                                                        │
│                │   [保存] [取消]                                         │
└────────────────┴────────────────────────────────────────────────────────┘

目录说明：
- daily/     归档笔记（按年月组织）
- projects/  项目笔记
- personal/  个人信息
- topics/    主题笔记
- pending/   临时笔记
- memory/    记忆目录（MEMORY.md + 每日笔记）
```

#### 3.5.4 技能页面设计

> **说明**：技能页面展示所有可用的技能，包括内置技能和用户自定义技能。
> 技能只能查看，不能通过 Web UI 创建或编辑。

```
┌─────────────────────────────────────────────────────────────────────────┐
│  技能                                    [内置技能] [自定义技能]          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐    │
│   │ 📝 memory        │  │ 📅 daily-note    │  │ 📦 archive       │    │
│   │                  │  │                  │  │                  │    │
│   │ 两层记忆系统     │  │ 自动创建每日笔记  │  │ 归档旧笔记       │    │
│   │                  │  │                  │  │                  │    │
│   │ [always: true]   │  │ [always: false]  │  │ [always: false]  │    │
│   │                  │  │                  │  │                  │    │
│   │ [查看详情]       │  │ [查看详情]       │  │ [查看详情]       │    │
│   └──────────────────┘  └──────────────────┘  └──────────────────┘    │
│                                                                         │
│   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐    │
│   │ 🔍 note-search   │  │ ⏰ cron          │  │ 🌤️ weather       │    │
│   │                  │  │                  │  │                  │    │
│   │ 语义搜索笔记     │  │ 定时任务管理     │  │ 天气查询         │    │
│   │                  │  │                  │  │                  │    │
│   │ [always: false]  │  │ [always: false]  │  │ [always: false]  │    │
│   │                  │  │                  │  │                  │    │
│   │ [查看详情]       │  │ [查看详情]       │  │ [查看详情]       │    │
│   └──────────────────┘  └──────────────────┘  └──────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

技能详情弹窗：
┌─────────────────────────────────────────┐
│  📝 memory                          [×]  │
├─────────────────────────────────────────┤
│                                         │
│  name: memory                           │
│  description: Two-layer memory system   │
│  always: true                           │
│                                         │
│  ─────────────────────────────────────  │
│                                         │
│  ## Structure                           │
│                                         │
│  - `memory/MEMORY.md` — Long-term facts │
│  - `memory/HISTORY.md` — Event log      │
│  ...                                    │
│                                         │
└─────────────────────────────────────────┘
```

#### 3.5.5 配置页面设计

> **说明**：配置页面用于查看和修改 nanobot 的配置。
> 敏感信息（如 API Key）只显示脱敏值，编辑时需要重新输入完整值。

```
┌─────────────────────────────────────────────────────────────────────────┐
│  配置                                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │ 模型配置                                                         │  │
│   │                                                                  │  │
│   │ 当前模型: [anthropic/claude-opus-4-5        ▼]                   │  │
│   │                                                                  │  │
│   │ 提供商配置:                                                      │  │
│   │   ☑ OpenAI      API Key: sk-****...**** [编辑]                  │  │
│   │   ☑ Anthropic   API Key: sk-ant-****... [编辑]                  │  │
│   │   ☑ DeepSeek    API Key: sk-****...**** [编辑]                  │  │
│   │   ☐ OpenRouter  API Key: [未配置]       [配置]                  │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │ 知识检索配置                                                     │  │
│   │                                                                  │  │
│   │ 启用向量检索: [☑]                                                │  │
│   │ 嵌入模型: [BAAI/bge-small-zh-v1.5          ▼]                    │  │
│   │ 内存限制: 500MB - 1000MB                                         │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │ 通信渠道                                                         │  │
│   │                                                                  │  │
│   │ ☑ Web UI      端口: 8080                        [已启用]         │  │
│   │ ☐ Telegram    token: [未配置]                   [配置]          │  │
│   │ ☐ Feishu      app_id: [未配置]                  [配置]          │  │
│   │ ☐ Discord     token: [未配置]                   [配置]          │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│                                              [保存配置] [重置]          │
└─────────────────────────────────────────────────────────────────────────┘

安全说明：
- API Key 等敏感信息只显示脱敏值（如 sk-****...****）
- 编辑敏感信息时需要重新输入完整值
- 配置修改后需要重启服务才能生效
```

---

## 四、技能系统扩展

### 4.1 每日笔记技能 (skills/daily-note/SKILL.md)

```markdown
---
name: daily-note
description: 自动创建和管理每日笔记
always: false
---

# 每日笔记技能

## 功能

- 自动在 `memory/` 目录下创建每日笔记文件 `YYYY-MM-DD.md`
- 支持追加内容到当日笔记
- 支持查看最近几天的笔记

## 使用方式

### 创建今日笔记

使用 `write_file` 工具创建 `memory/YYYY-MM-DD.md` 文件。

### 追加内容

使用 `edit_file` 工具追加内容到当日笔记。

### 查看笔记

使用 `read_file` 工具读取指定日期的笔记。

## 文件位置

- 每日笔记: `workspace/memory/YYYY-MM-DD.md`
- 保留期限: 最近 7 天（自动归档）

## 注意事项

- 每日笔记应简洁，记录关键信息
- 超过 7 天的笔记会被归档技能自动移动到 `daily/YYYY/MM/` 目录
```

### 4.2 归档技能 (skills/archive/SKILL.md)

```markdown
---
name: archive
description: 归档旧笔记，控制记忆上下文大小
always: false
---

# 归档技能

## 功能

- 将超过保留期限的每日笔记移动到归档目录
- 按年月组织归档文件
- 保持 `memory/` 目录整洁

## 归档规则

| 文件类型 | 保留期限 | 归档位置                      |
| -------- | -------- | ----------------------------- |
| 每日笔记 | 7 天     | `daily/YYYY/MM/YYYY-MM-DD.md` |

## 使用方式

### 手动归档

移动超过 7 天的每日笔记到归档目录：

- 源: memory/2026-02-20.md
- 目标: daily/2026/02/2026-02-20.md

### 自动归档

建议配置 cron 任务每日执行归档。

## 目录结构
```

workspace/
├── memory/ # 最近 7 天的每日笔记
│ ├── 2026-02-22.md
│ └── ...
└── daily/ # 归档笔记
└── 2026/
└── 02/
├── 2026-02-01.md
└── ...

```

## Token 优化

归档后，`memory/` 目录只保留最近 7 天的笔记，大幅减少日常使用的上下文大小。
```

---

## 五、配置扩展

在 `config/schema.py` 中新增 Web UI 配置：

```python
class WebUIConfig(Base):
    """Web UI 配置"""

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8080

class GatewayConfig(Base):
    """Gateway 配置（扩展）"""

    host: str = "0.0.0.0"
    port: int = 18790
    heartbeat: HeartbeatConfig = Field(default_factory=HeartbeatConfig)
    web_ui: WebUIConfig = Field(default_factory=WebUIConfig)
```

---

## 六、实施步骤

### 6.1 阶段一：知识检索模块 ✅ 已完成

| 序号 | 任务                               | 优先级 | 状态 |
| ---- | ---------------------------------- | ------ | ---- |
| 1.1  | 创建 `nanobot/knowledge/` 目录结构 | 高     | ✅   |
| 1.2  | 实现 `HybridRetriever` 类          | 高     | ✅   |
| 1.3  | 实现 `NoteProcessor` 类            | 中     | ✅   |
| 1.4  | 实现 `BM25Persist` 类              | 高     | ✅   |
| 1.5  | 实现 `IncrementalIndexer` 类       | 高     | ✅   |
| 1.6  | 实现 `QueryCache` 类               | 中     | ✅   |
| 1.7  | 扩展配置 schema                    | 高     | ✅   |
| 1.8  | 实现 NoteSearchTool                | 高     | ✅   |
| 1.9  | 单元测试                           | 中     | ✅   |

### 6.2 阶段二：技能系统扩展

| 序号 | 任务                 | 优先级 | 交付物                     |
| ---- | -------------------- | ------ | -------------------------- |
| 2.1  | 创建 daily-note 技能 | 高     | skills/daily-note/SKILL.md |
| 2.2  | 创建 archive 技能    | 高     | skills/archive/SKILL.md    |

### 6.3 阶段三：Web 后端 API

| 序号 | 任务                         | 优先级 | 交付物           |
| ---- | ---------------------------- | ------ | ---------------- |
| 3.1  | 创建 `nanobot/web/` 目录结构 | 高     | 目录结构         |
| 3.2  | 实现 FastAPI 服务入口        | 高     | server.py        |
| 3.3  | 实现对话 API                 | 高     | routes/chat.py   |
| 3.4  | 实现笔记 API                 | 高     | routes/notes.py  |
| 3.5  | 实现技能 API                 | 中     | routes/skills.py |
| 3.6  | 实现配置 API                 | 中     | routes/config.py |
| 3.7  | 集成到 gateway 命令          | 高     | commands.py 修改 |

### 6.4 阶段四：Web 前端界面

| 序号 | 任务              | 优先级 | 交付物               |
| ---- | ----------------- | ------ | -------------------- |
| 4.1  | 创建 Vue 项目结构 | 高     | custom/web-frontend/ |
| 4.2  | 实现对话页面      | 高     | views/Chat.vue       |
| 4.3  | 实现笔记页面      | 高     | views/Notes.vue      |
| 4.4  | 实现技能页面      | 中     | views/Skills.vue     |
| 4.5  | 实现配置页面      | 中     | views/Config.vue     |
| 4.6  | 响应式布局适配    | 中     | TailwindCSS 样式     |
| 4.7  | 编译集成到后端    | 高     | static/ 目录         |

### 6.5 阶段五：测试与文档

| 序号 | 任务     | 优先级 | 交付物              |
| ---- | -------- | ------ | ------------------- |
| 5.1  | 集成测试 | 高     | test_integration.py |
| 5.2  | 性能测试 | 中     | 测试报告            |
| 5.3  | 用户文档 | 中     | docs/web-ui.md      |
| 5.4  | API 文档 | 中     | OpenAPI schema      |

---

## 七、资源需求

### 7.1 技术资源

| 资源       | 规格                       | 用途       |
| ---------- | -------------------------- | ---------- |
| 开发环境   | Python 3.11+               | 代码开发   |
| 嵌入模型   | bge-small-zh-v1.5 (~400MB) | 本地向量化 |
| 向量数据库 | ChromaDB (~50MB)           | 向量存储   |
| 内存需求   | 最低 512MB，推荐 1GB       | 模型加载   |
| Node.js    | 18+                        | 前端编译   |

### 7.2 内存占用分析

| 组件                   | 内存占用        | 说明         |
| ---------------------- | --------------- | ------------ |
| bge-small-zh-v1.5 模型 | ~400MB          | 加载到内存   |
| ChromaDB 索引          | ~100MB/10万向量 | 随数据量增长 |
| 运行时缓存             | ~100MB          | 查询缓存     |
| FastAPI 服务           | ~50MB           | Web 服务     |
| **总计（推荐）**       | **~650MB**      | 舒适运行     |

---

## 八、风险评估

### 8.1 技术风险

| 风险             | 概率 | 影响 | 应对策略                     |
| ---------------- | ---- | ---- | ---------------------------- |
| 模型下载失败     | 中   | 低   | 提供离线模型包，国内镜像     |
| 内存占用过高     | 低   | 中   | 监控内存，提供轻量模型选项   |
| 中文检索效果不佳 | 低   | 高   | bge-small-zh-v1.5 已验证     |
| 前端兼容性问题   | 低   | 中   | 使用成熟框架，测试主流浏览器 |

### 8.2 兼容性风险

| 风险              | 概率 | 影响 | 应对策略                 |
| ----------------- | ---- | ---- | ------------------------ |
| 旧配置不兼容      | 低   | 低   | 配置迁移脚本，默认值兼容 |
| Python 版本不兼容 | 低   | 中   | 明确要求 Python 3.11+    |

---

## 九、总结

### 9.1 方案要点

| 维度         | 方案                                  |
| ------------ | ------------------------------------- |
| **已完成**   | 混合检索记忆系统（BM25 + 向量 + RRF） |
| **待开发**   | Web 界面 + 技能扩展                   |
| **嵌入模型** | bge-small-zh-v1.5 (~400MB)            |
| **内存占用** | ~650MB                                |
| **Web 框架** | FastAPI + Vue 3                       |

### 9.2 预期效果

| 维度           | 提升效果             |
| -------------- | -------------------- |
| 笔记检索准确率 | +70%（语义理解）     |
| Token 效率     | -50%（按需检索）     |
| 用户体验       | Web 界面，无需命令行 |
| 内存占用       | ~650MB（符合约束）   |

### 9.3 适用场景

本方案特别适合：

- ✅ 有大量笔记需要检索的用户
- ✅ 需要每日笔记管理的用户
- ✅ 希望 Web 界面操作的用户
- ✅ 中文笔记为主的使用场景
- ✅ 内存资源有限（推荐 1GB+）
