# JinshiAgent 🤖

> AI Agent 工具集 — 让智能体开发更简单

JinshiAgent 是一个面向 AI Agent 开发者的工具仓库，提供智能体编排、工具调用、记忆管理和多轮对话等核心能力的封装与实现。目标是降低 Agent 应用的开发门槛，提供开箱即用的模块化组件。

## 项目定位

- **类型**：AI Agent 工具框架 / 工具集
- **语言**：Python 3.11+
- **目标用户**：需要快速搭建智能体应用的开发者
- **核心理念**：模块化、可组合、易扩展

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.11+ | 主开发语言 |
| 包管理 | uv / pip | 依赖管理与虚拟环境 |
| LLM 接入 | OpenAI API / 兼容接口 | 大语言模型调用层 |
| 工具调用 | Function Calling | 结构化工具定义与执行 |
| 向量存储 | ChromaDB / FAISS | 语义检索与记忆存储 |
| 测试 | pytest | 单元测试与集成测试 |
| 代码质量 | Ruff + mypy | 格式化、lint 与类型检查 |

## 功能规划

### Phase 1 — 核心框架（基础能力）

- [ ] **Agent 基类**：统一 Agent 生命周期管理（初始化、执行、停止）
- [ ] **消息协议**：定义标准化的消息格式（User / Assistant / Tool / System）
- [ ] **工具注册中心**：装饰器驱动的工具定义与自动发现
- [ ] **LLM 调用层**：封装 OpenAI 兼容接口，支持流式输出
- [ ] **配置管理**：YAML / 环境变量驱动的配置体系

### Phase 2 — 记忆与编排（进阶能力）

- [ ] **短期记忆**：对话上下文窗口管理与摘要压缩
- [ ] **长期记忆**：基于向量数据库的持久化存储与检索
- [ ] **ReAct 循环**：思考→行动→观察的推理执行框架
- [ ] **多 Agent 协作**：Agent 间的任务分发与结果聚合
- [ ] **工作流引擎**：DAG 驱动的多步骤任务编排

### Phase 3 — 工具生态（扩展能力）

- [ ] **内置工具集**：文件操作、代码执行、Web 搜索、API 调用
- [ ] **MCP 协议支持**：接入 Model Context Protocol 工具生态
- [ ] **自定义工具 SDK**：简化第三方工具的开发与接入流程
- [ ] **沙箱执行环境**：安全的代码运行隔离机制

### Phase 4 — 平台化（生产就绪）

- [ ] **API 服务**：FastAPI 封装的 Agent 调用接口
- [ ] **Web UI**：对话式交互界面
- [ ] **监控与日志**：Agent 运行状态追踪与调试工具
- [ ] **部署方案**：Docker / 云函数一键部署模板

## 项目结构（规划）

```
jinshiagent/
├── src/
│   └── jinshiagent/
│       ├── core/           # Agent 基类与消息协议
│       ├── llm/            # LLM 调用层封装
│       ├── memory/         # 记忆管理（短期 + 长期）
│       ├── tools/          # 内置工具集
│       ├── workflow/       # 工作流编排引擎
│       └── config/         # 配置管理
├── tests/                  # 测试用例
├── examples/               # 使用示例
├── docs/                   # 项目文档
├── pyproject.toml          # 项目元数据与依赖
└── README.md
```

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/jinshi678/jinshiagent.git
cd jinshiagent

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -e .

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入你的 OPENAI_API_KEY
```

## 开发指南

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化与检查
ruff check . && ruff format .
mypy src/
```

## 贡献

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交修改：`git commit -m "feat: add your feature"`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

## 许可证

MIT License

## 链接

- **仓库**：https://github.com/jinshi678/jinshiagent
- **问题反馈**：https://github.com/jinshi678/jinshiagent/issues
