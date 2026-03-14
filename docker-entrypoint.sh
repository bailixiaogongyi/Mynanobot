#!/bin/bash
set -e

CONFIG_FILE="/root/.nanobot/config.json"
WORKSPACE_DIR="/root/.nanobot/workspace"
KNOWLEDGE_DIR="/root/.nanobot/knowledge"
CRON_DIR="/root/.nanobot/cron"

echo "========================================"
echo "  AiMate Docker Initialization"
echo "========================================"

# 创建必要的目录
mkdir -p "$(dirname "$CONFIG_FILE")"
mkdir -p "$WORKSPACE_DIR"
mkdir -p "$KNOWLEDGE_DIR"
mkdir -p "$CRON_DIR"

# 检查配置文件是否存在，不存在则创建默认配置
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[nanobot] Creating default configuration..."
    
    # 创建默认配置文件（与 nanobot onboard 生成的配置一致）
    cat > "$CONFIG_FILE" << 'EOF'
{
  "agents": {
    "defaults": {
      "workspace": "~/.nanobot/workspace",
      "model": "anthropic/claude-opus-4-5",
      "max_tokens": 8192,
      "temperature": 0.1,
      "max_tool_iterations": 40,
      "memory_window": 100
    }
  },
  "providers": {
    "custom": { "api_key": "" },
    "anthropic": { "api_key": "" },
    "openai": { "api_key": "" },
    "openrouter": { "api_key": "" },
    "deepseek": { "api_key": "" },
    "groq": { "api_key": "" },
    "zhipu": { "api_key": "" },
    "dashscope": { "api_key": "" },
    "vllm": { "api_key": "" },
    "gemini": { "api_key": "" },
    "moonshot": { "api_key": "" },
    "minimax": { "api_key": "" },
    "aihubmix": { "api_key": "" },
    "siliconflow": { "api_key": "" },
    "volcengine": { "api_key": "" },
    "openai_codex": { "api_key": "" },
    "github_copilot": { "api_key": "" }
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
        "api_key": "",
        "max_results": 10
      }
    },
    "weather": {
      "weather": {
        "api_key": ""
      }
    },
    "exec": {
      "timeout": 60
    },
    "restrict_to_workspace": false,
    "mcp_servers": {},
    "knowledge": {
      "index": {
        "enabled": false,
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
  },
  "channels": {
    "send_progress": true,
    "send_tool_hints": false,
    "whatsapp": {
      "enabled": false,
      "bridge_url": "ws://localhost:3001",
      "bridge_token": "",
      "allow_from": []
    },
    "telegram": {
      "enabled": false,
      "token": "",
      "allow_from": [],
      "proxy": null,
      "reply_to_message": false
    },
    "discord": {
      "enabled": false,
      "token": "",
      "allow_from": [],
      "gateway_url": "wss://gateway.discord.gg/?v=10&encoding=json",
      "intents": 37377
    },
    "feishu": {
      "enabled": false,
      "app_id": "",
      "app_secret": "",
      "encrypt_key": "",
      "verification_token": "",
      "allow_from": []
    },
    "dingtalk": {
      "enabled": false,
      "client_id": "",
      "client_secret": "",
      "allow_from": []
    },
    "email": {
      "enabled": false,
      "consent_granted": false,
      "imap_host": "",
      "imap_port": 993,
      "imap_username": "",
      "imap_password": "",
      "imap_mailbox": "INBOX",
      "imap_use_ssl": true,
      "smtp_host": "",
      "smtp_port": 587,
      "smtp_username": "",
      "smtp_password": "",
      "smtp_use_tls": true,
      "smtp_use_ssl": false,
      "from_address": "",
      "auto_reply_enabled": true,
      "poll_interval_seconds": 30,
      "mark_seen": true,
      "max_body_chars": 12000,
      "subject_prefix": "Re: ",
      "allow_from": []
    },
    "slack": {
      "enabled": false,
      "mode": "socket",
      "webhook_path": "/slack/events",
      "bot_token": "",
      "app_token": "",
      "user_token_read_only": true,
      "reply_in_thread": true,
      "react_emoji": "eyes",
      "group_policy": "mention",
      "group_allow_from": [],
      "dm": {
        "enabled": true,
        "policy": "open",
        "allow_from": []
      }
    },
    "qq": {
      "enabled": false,
      "app_id": "",
      "secret": "",
      "allow_from": []
    }
  }
}
EOF
    
    echo "[AiMate] Default configuration created at $CONFIG_FILE"
    echo "[AiMate] Please add your API keys via Web UI or edit the config file"
fi

# 创建工作空间模板文件（如果不存在）
_create_workspace_templates() {
    local workspace="$1"
    
    # 创建 memory 目录
    mkdir -p "$workspace/memory"
    
    # 创建 MEMORY.md
    if [ ! -f "$workspace/memory/MEMORY.md" ]; then
        cat > "$workspace/memory/MEMORY.md" << 'EOF'
# Memory

This file stores important information that should be remembered across conversations.

## User Preferences


## Important Notes

EOF
        echo "[AiMate] Created memory/MEMORY.md"
    fi
    
    # 创建 HISTORY.md
    if [ ! -f "$workspace/memory/HISTORY.md" ]; then
        touch "$workspace/memory/HISTORY.md"
        echo "[AiMate] Created memory/HISTORY.md"
    fi
    
    # 创建 SOUL.md
    if [ ! -f "$workspace/SOUL.md" ]; then
        cat > "$workspace/SOUL.md" << 'EOF'
# AiMate Soul

I am AiMate, a personal AI assistant.

## Core Traits

- Helpful and proactive
- Clear and concise communication
- Respect user privacy and preferences

## Capabilities

- Answer questions and provide information
- Help with coding and technical tasks
- Manage notes and knowledge
- Execute shell commands (with permission)
- Search the web for current information

EOF
        echo "[AiMate] Created SOUL.md"
    fi
    
    # 创建 TOOLS.md
    if [ ! -f "$workspace/TOOLS.md" ]; then
        cat > "$workspace/TOOLS.md" << 'EOF'
# Tools Usage Log

This file tracks tool usage patterns and preferences.

EOF
        echo "[AiMate] Created TOOLS.md"
    fi
    
    # 创建 skills 目录
    mkdir -p "$workspace/skills"
}

# 初始化工作空间
echo "[AiMate] Initializing workspace..."
_create_workspace_templates "$WORKSPACE_DIR"

# 显示配置状态
echo ""
echo "========================================"
echo "  Configuration Status"
echo "========================================"

# 检查是否有 API key 配置
HAS_API_KEY=false
if grep -q '"api_key": "[^"]' "$CONFIG_FILE" 2>/dev/null; then
    HAS_API_KEY=true
fi

if [ "$HAS_API_KEY" = true ]; then
    echo "[OK] API keys configured"
else
    echo "[WARNING] No API keys configured!"
    echo ""
    echo "  Please configure your API keys:"
    echo "  1. Web UI: http://localhost:8080 → Settings"
    echo "  2. Or edit: ~/.nanobot/config.json"
    echo ""
    echo "  Then restart the service:"
    echo "  docker compose restart nanobot-gateway"
fi

echo ""
echo "[AiMate] Starting gateway service..."
echo "  Web UI: http://0.0.0.0:8080"
echo "  API: http://0.0.0.0:18790"
echo ""

# 启动 gateway 服务
exec nanobot gateway
