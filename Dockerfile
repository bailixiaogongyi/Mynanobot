# ✅ 使用国内镜像加速器
FROM docker.1ms.run/python:3.12-slim-bookworm

LABEL maintainer="AiMate contributors"
LABEL description="Ultra-Lightweight Personal AI Assistant"
LABEL version="0.1.4.post2"

# ✅ 优化1：使用腾讯云镜像源（腾讯云环境优化）
RUN echo 'deb https://mirrors.cloud.tencent.com/debian/ bookworm main' > /etc/apt/sources.list && \
    echo 'deb https://mirrors.cloud.tencent.com/debian/ bookworm-updates main' >> /etc/apt/sources.list && \
    echo 'deb https://mirrors.cloud.tencent.com/debian-security bookworm-security main' >> /etc/apt/sources.list

# ✅ 优化2：安装系统依赖（增加重试机制）
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制项目文件
COPY pyproject.toml README.md LICENSE ./
COPY nanobot/ nanobot/
COPY bridge/ bridge/

# ✅ 优化3：配置 pip 全局设置（增加超时和重试）
RUN pip config set global.timeout 300 && \
    pip config set global.retries 10 && \
    pip config set global.trusted-host "pypi.tuna.tsinghua.edu.cn mirrors.aliyun.com pypi.doubanio.com"

# ✅ 优化4：安装基础依赖（使用清华源 + 阿里源备份）
RUN pip install --no-cache-dir \
    --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    --extra-index-url https://mirrors.aliyun.com/pypi/simple/ \
    . || \
    pip install --no-cache-dir \
    --index-url https://mirrors.aliyun.com/pypi/simple/ \
    .

# ✅ 优化5：安装 CPU 版 PyTorch（使用清华源 + PyTorch 官方源）
RUN pip install --no-cache-dir \
    --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch torchvision torchaudio || \
    pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch torchvision torchaudio

# ✅ 优化6：安装完整依赖（多源备份）
RUN pip install --no-cache-dir \
    --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    --extra-index-url https://mirrors.aliyun.com/pypi/simple/ \
    ".[web-ui,docx,pdf,excel,pptx,ocr,knowledge]" || \
    pip install --no-cache-dir \
    --index-url https://mirrors.aliyun.com/pypi/simple/ \
    ".[web-ui,docx,pdf,excel,pptx,ocr,knowledge]"

# ✅ 优化7：安装 Node.js 和构建前端（使用淘宝镜像）
RUN apt-get update && \
    apt-get install -y --no-install-recommends nodejs npm && \
    rm -rf /var/lib/apt/lists/* && \
    cd bridge && \
    npm config set registry https://registry.npmmirror.com && \
    npm install --registry=https://registry.npmmirror.com && \
    npm run build && \
    cd ..

# 数据目录
RUN mkdir -p /root/.nanobot

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 18790
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
