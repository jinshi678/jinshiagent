# JinshiAgent 部署指南

本文档介绍如何在不同环境下部署 JinshiAgent。

---

## 目录

1. [本地开发运行](#1-本地开发运行)
2. [API 服务部署](#2-api-服务部署)
3. [Web UI 部署](#3-web-ui-部署)
4. [Docker 部署](#4-docker-部署)
5. [腾讯云服务器部署](#5-腾讯云服务器部署)
6. [API 调用示例](#6-api-调用示例)
7. [环境变量说明](#7-环境变量说明)
8. [常见问题](#8-常见问题)

---

## 1. 本地开发运行

### 前置条件

- Python 3.11+
- pip 或 uv 包管理器

### 安装

```bash
# 克隆项目
git clone https://github.com/jinshi678/jinshiagent.git
cd jinshiagent

# 安装核心包
pip install -e .

# 安装全部可选依赖（含 ChromaDB、Streamlit 等）
pip install -e ".[all]"
```

### 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入实际的 API Key
# OPENAI_API_KEY=sk-your-actual-key
```

### 验证安装

```bash
# 运行测试
pytest tests/ -v

# 快速验证
python -c "from jinshiagent import __version__; print(f'JinshiAgent v{__version__}')"
```

---

## 2. API 服务部署

### 启动 FastAPI 服务

```bash
# 方式一：使用内置命令
jinshiagent-server

# 方式二：使用 uvicorn 直接启动
uvicorn jinshiagent.server:app --host 0.0.0.0 --port 8000

# 方式三：带 API 密钥认证
JINSHI_API_KEY=your-secret-key uvicorn jinshiagent.server:app --host 0.0.0.0 --port 8000

# 方式四：开发模式（自动重载）
JINSHI_RELOAD=1 jinshiagent-server
```

### 启动后

- API 文档：http://localhost:8000/docs（Swagger UI）
- 健康检查：http://localhost:8000/health

### 生产环境推荐

```bash
# 使用多个 worker 进程
uvicorn jinshiagent.server:app --host 0.0.0.0 --port 8000 --workers 4

# 使用 Gunicorn + Uvicorn worker
pip install gunicorn
gunicorn jinshiagent.server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## 3. Web UI 部署

### 启动 Streamlit

```bash
# 确保 API 服务已启动
jinshiagent-server &

# 启动 Web UI
cd web/
streamlit run app.py --server.port 8501
```

### 访问

- Web UI：http://localhost:8501

### 配置

在 Web UI 的侧边栏中配置：
- **API 地址**：默认 `http://localhost:8000`
- **API 密钥**：如果服务端启用了认证，需提供对应密钥
- **系统提示词**：自定义 Agent 的行为

---

## 4. Docker 部署

### 快速启动

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY

# 2. 一键启动（API + Web UI）
docker compose up -d

# 3. 查看日志
docker compose logs -f

# 4. 停止服务
docker compose down
```

### 仅启动 API 服务

```bash
docker compose up -d api
```

### 仅启动 Web UI

```bash
# 需要先启动 API 服务
docker compose up -d api
docker compose up -d web
```

### 自定义构建

```bash
# 构建镜像
docker build -t jinshiagent:latest .

# 手动运行 API
docker run -d \
  --name jinshiagent-api \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-your-key \
  -v jinshiagent-data:/app/data \
  jinshiagent:latest

# 手动运行 Web UI
docker run -d \
  --name jinshiagent-web \
  -p 8501:8501 \
  --link jinshiagent-api:api \
  jinshiagent:latest \
  streamlit run web/app.py --server.port=8501 --server.address=0.0.0.0
```

### 端口说明

| 服务 | 默认端口 | 环境变量 |
|------|----------|----------|
| API 服务 | 8000 | `JINSHI_PORT` |
| Web UI | 8501 | — |
| Swagger 文档 | 8000/docs | — |

---

## 5. 腾讯云服务器部署

### 服务器准备

```bash
# 1. 安装 Docker（以 Ubuntu 为例）
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. 安装 Docker Compose
sudo apt install docker-compose-plugin

# 3. 克隆项目
git clone https://github.com/jinshi678/jinshiagent.git
cd jinshiagent
```

### 部署步骤

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env：
#   OPENAI_API_KEY=sk-your-key
#   JINSHI_API_KEY=your-internal-api-key  # 生产环境建议设置
#   JINSHI_PORT=8000

# 2. 构建并启动
docker compose up -d --build

# 3. 验证服务
curl http://localhost:8000/health

# 4. 配置防火墙/安全组
# 开放 8000 端口（API）和 8501 端口（Web UI）
```

### 使用 Nginx 反向代理（推荐）

```nginx
server {
    listen 80;
    server_name agent.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
    }

    location /web/ {
        proxy_pass http://127.0.0.1:8501/;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 使用 HTTPS（Let's Encrypt）

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d agent.yourdomain.com

# 自动续期已由 Certbot 定时任务处理
```

---

## 6. API 调用示例

### 健康检查

```bash
curl http://localhost:8000/health
```

### 对话

```bash
# 创建新对话
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，请介绍一下你自己"}'

# 继续对话（使用返回的 session_id）
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "刚才我们聊了什么？", "session_id": "abc12345"}'
```

### 带认证的请求

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-key" \
  -d '{"message": "你好"}'
```

### 工具调用

```bash
# 列出工具
curl http://localhost:8000/tools

# 调用工具
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "calculator", "arguments": {"expression": "2 + 3 * 4"}}'
```

### 记忆管理

```bash
# 添加记忆
curl -X POST http://localhost:8000/memory/add \
  -H "Content-Type: application/json" \
  -d '{"content": "用户偏好使用 Python 编程", "role": "system", "topic": "preference"}'

# 搜索记忆
curl -X POST http://localhost:8000/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "编程语言偏好", "n_results": 5}'

# 查看所有记忆
curl http://localhost:8000/memory/all?limit=20
```

### 多 Agent 协作

```bash
# Orchestrator 模式
curl -X POST http://localhost:8000/multi-agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "task": "分析 AI Agent 市场趋势并撰写报告",
    "mode": "orchestrator"
  }'

# Pipeline 模式（自定义 Agent）
curl -X POST http://localhost:8000/multi-agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "task": "研究并总结量子计算最新进展",
    "mode": "pipeline",
    "agent_configs": [
      {"name": "researcher", "system_prompt": "你负责调研和分析问题"},
      {"name": "writer", "system_prompt": "你负责撰写和总结内容"}
    ]
  }'
```

### Python 调用

```python
import httpx

API_URL = "http://localhost:8000"
headers = {"Authorization": "Bearer your-secret-key"} if API_KEY else {}

# 对话
response = httpx.post(
    f"{API_URL}/chat",
    json={"message": "你好", "session_id": None},
    headers=headers,
    timeout=60.0,
)
result = response.json()
print(result["response"])
print(f"Session: {result['session_id']}")

# 搜索记忆
response = httpx.post(
    f"{API_URL}/memory/search",
    json={"query": "用户偏好", "n_results": 5},
    headers=headers,
)
memories = response.json()
for m in memories:
    print(f"[{m['score']:.2f}] {m['content']}")
```

---

## 7. 环境变量说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENAI_API_KEY` | — | **必填**，OpenAI API 密钥 |
| `OPENAI_API_BASE` | `https://api.openai.com/v1` | API 基础 URL（支持兼容接口） |
| `JINSHI_MODEL` | `gpt-4o` | 默认模型名称 |
| `JINSHI_API_KEY` | 空 | API 认证密钥（留空不启用认证） |
| `JINSHI_HOST` | `0.0.0.0` | API 服务绑定地址 |
| `JINSHI_PORT` | `8000` | API 服务端口 |
| `JINSHI_RELOAD` | `0` | 开发模式自动重载（1=启用） |

---

## 8. 常见问题

### Q: 启动后提示 "LLM 服务未配置"

**A:** 需要设置 `OPENAI_API_KEY` 环境变量，或在 `.env` 文件中配置。

### Q: Docker 构建时 ChromaDB 安装失败

**A:** Docker 镜像已包含内置向量存储后端，不依赖 ChromaDB。LongTermMemory 会自动降级为纯 Python 后端。

### Q: 如何在腾讯云上使用内网加速

**A:** 如果使用代理或自建中转服务，设置 `OPENAI_API_BASE` 指向内网地址：
```bash
OPENAI_API_BASE=http://your-internal-proxy:8080/v1
```

### Q: Web UI 连不上 API 服务

**A:** 检查：
1. API 服务是否已启动（`curl http://localhost:8000/health`）
2. Web UI 的 API 地址配置是否正确（侧边栏 → API 地址）
3. Docker 环境中是否使用了正确的网络

### Q: 如何限制 API 访问

**A:** 设置 `JINSHI_API_KEY` 环境变量后，所有请求需携带 `Authorization: Bearer <key>` 头。

### Q: 记忆数据存在哪里

**A:**
- 本地运行：`./data/memory/` 目录
- Docker 运行：`jinshiagent-data` 数据卷
- 可通过 `persist_directory` 参数自定义路径
