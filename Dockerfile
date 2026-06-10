# ── 多阶段构建 ──────────────────────────────────────────────────────────
# Stage 1: 构建阶段 — 安装依赖
# Stage 2: 运行阶段 — 精简镜像

FROM python:3.12-slim AS builder

WORKDIR /build

# 复制项目文件
COPY pyproject.toml README.md ./
COPY src/ src/

# 安装依赖到 /install 目录
RUN pip install --no-cache-dir --prefix=/install . && \
    pip install --no-cache-dir --prefix=/install uvicorn fastapi

# ── 运行阶段 ──────────────────────────────────────────────────────────

FROM python:3.12-slim

LABEL maintainer="jinshi678"
LABEL description="JinshiAgent — AI Agent 工具框架"
LABEL version="0.5.0"

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

# 安装运行时依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# 从构建阶段复制 Python 包
COPY --from=builder /install /usr/local

# 创建非 root 用户
RUN groupadd -r jinshi && useradd -r -g jinshi -d /app jinshi

# 创建数据目录
RUN mkdir -p /app/data/memory && chown -R jinshi:jinshi /app

WORKDIR /app

# 复制项目文件
COPY --chown=jinshi:jinshi . .

# 切换到非 root 用户
USER jinshi

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 默认启动 FastAPI 服务
CMD ["uvicorn", "jinshiagent.server:app", "--host", "0.0.0.0", "--port", "8000"]
