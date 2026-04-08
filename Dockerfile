FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

LABEL maintainer="AiMate contributors"
LABEL description="Ultra-Lightweight Personal AI Assistant"
LABEL version="0.1.4.post2"

# 更换为清华镜像源（加速 Debian 包下载）
RUN echo 'deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main' > /etc/apt/sources.list && \
    echo 'deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main' >> /etc/apt/sources.list && \
    echo 'deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main' >> /etc/apt/sources.list

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates gnupg git && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get purge -y gnupg && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
RUN mkdir -p nanobot bridge && touch nanobot/__init__.py && \
    uv pip install --system --no-cache -i https://pypi.tuna.tsinghua.edu.cn/simple . && \
    rm -rf nanobot bridge

COPY nanobot/ nanobot/
COPY bridge/ bridge/
# 1. 使用 pip 直接安装 PyTorch CPU-only 版本（避免安装 GPU 版本造成镜像过大）
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
# 2. 使用清华镜像源安装其他 Python 依赖（包含 knowledge，但不会重新安装 GPU torch）
RUN uv pip install --system --no-cache -i https://pypi.tuna.tsinghua.edu.cn/simple ".[web-ui,docx,pdf,excel,pptx,ocr,knowledge]" .

WORKDIR /app/bridge
# 使用淘宝镜像源安装 Node.js 依赖
RUN npm config set registry https://registry.npmmirror.com && npm install && npm run build
WORKDIR /app

RUN mkdir -p /root/.nanobot

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 18790
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]