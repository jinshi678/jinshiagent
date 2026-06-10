"""FastAPI HTTP API 服务 — 为 JinshiAgent 提供完整的 Web 接口

提供以下功能：
    - 对话交互：单轮/多轮对话，流式响应
    - 工具调用：查看已注册工具、执行工具
    - 记忆管理：搜索/添加/删除长期记忆
    - 多 Agent 协作：Orchestrator / Pipeline / Team 模式
    - API 密钥认证：防止未授权访问
    - 健康检查：/health 端点

启动方式::

    # 直接运行
    python -m jinshiagent.server

    # uvicorn 启动
    uvicorn jinshiagent.server:app --host 0.0.0.0 --port 8000

    # 带认证
    JINSHI_API_KEY=your-secret-key uvicorn jinshiagent.server:app --host 0.0.0.0

API 文档：启动后访问 http://localhost:8000/docs
"""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from jinshiagent.core.agent import Agent
from jinshiagent.core.message import Message
from jinshiagent.core.multi_agent import (
    AgentTeam,
    Orchestrator,
    Pipeline,
    SubAgent,
    TeamMode,
)
from jinshiagent.core.tool_registry import ToolRegistry
from jinshiagent.llm.client import LLMClient, LLMConfig
from jinshiagent.memory.long_term import LongTermMemory

logger = logging.getLogger("jinshiagent.server")

# ---------------------------------------------------------------------------
# 全局状态：管理 Agent 会话池
# ---------------------------------------------------------------------------

_agent_pool: dict[str, Agent] = {}
_llm_client: LLMClient | None = None
_tool_registry: ToolRegistry | None = None
_default_memory: LongTermMemory | None = None
_api_key: str | None = None


def _get_api_key() -> str | None:
    """从环境变量读取 API 密钥。"""
    return os.getenv("JINSHI_API_KEY", "") or None


def _verify_api_key(authorization: str | None) -> None:
    """验证 API 密钥。"""
    key = _get_api_key()
    if not key:
        return  # 未配置密钥则跳过验证

    if not authorization:
        raise HTTPException(status_code=401, detail="缺少 Authorization 头")

    # 支持 "Bearer xxx" 和 "xxx" 两种格式
    token = authorization.replace("Bearer ", "").strip() if authorization else ""
    if token != key:
        raise HTTPException(status_code=403, detail="API 密钥无效")


def _init_default_components() -> None:
    """初始化默认组件（LLM、工具注册、长期记忆）。"""
    global _llm_client, _tool_registry, _default_memory, _api_key

    _api_key = _get_api_key()

    # 初始化 LLM 客户端
    try:
        api_key = os.getenv("OPENAI_API_KEY", "")
        api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        model = os.getenv("JINSHI_MODEL", "gpt-4o")

        if api_key:
            config = LLMConfig(api_key=api_key, api_base=api_base, model=model)
            _llm_client = LLMClient(config)
            logger.info("LLM 客户端已初始化 | model=%s", model)
        else:
            logger.warning("未配置 OPENAI_API_KEY，对话功能将不可用")
    except Exception as e:
        logger.warning("LLM 客户端初始化失败: %s", e)

    # 初始化工具注册中心
    _tool_registry = ToolRegistry()

    # 注册内置工具
    try:
        from jinshiagent.tools.calculator_tool import register as reg_calc
        from jinshiagent.tools.search_tool import register as reg_search
        from jinshiagent.tools.weather_tool import register as reg_weather

        reg_calc(_tool_registry)
        reg_search(_tool_registry)
        reg_weather(_tool_registry)
        logger.info("内置工具已注册: %s", _tool_registry.list_tools())
    except Exception as e:
        logger.warning("内置工具注册失败: %s", e)

    # 初始化默认长期记忆
    try:
        _default_memory = LongTermMemory(
            collection_name="default",
            persist_directory="./data/memory",
        )
        logger.info("默认长期记忆已初始化 | backend=%s", _default_memory.backend)
    except Exception as e:
        logger.warning("默认长期记忆初始化失败: %s", e)


# ---------------------------------------------------------------------------
# 请求/响应模型
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """对话请求。"""

    message: str = Field(..., min_length=1, description="用户消息")
    session_id: str | None = Field(None, description="会话 ID（不传则创建新会话）")
    system_prompt: str | None = Field(None, description="系统提示词")
    stream: bool = Field(False, description="是否流式返回")


class ChatResponse(BaseModel):
    """对话响应。"""

    session_id: str = Field(..., description="会话 ID")
    response: str = Field(..., description="Agent 回答")
    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list, description="本轮工具调用记录"
    )
    history_length: int = Field(0, description="对话历史条数")


class SessionResponse(BaseModel):
    """会话信息。"""

    session_id: str
    agent_name: str
    history_length: int
    has_long_term_memory: bool


class ToolInfo(BaseModel):
    """工具信息。"""

    name: str
    description: str
    parameters: dict[str, Any]


class ToolCallRequest(BaseModel):
    """工具调用请求。"""

    name: str = Field(..., description="工具名称")
    arguments: dict[str, Any] = Field(default_factory=dict, description="工具参数")


class ToolCallResponse(BaseModel):
    """工具调用响应。"""

    name: str
    result: str
    success: bool


class MemoryAddRequest(BaseModel):
    """添加记忆请求。"""

    content: str = Field(..., min_length=1, description="记忆内容")
    role: str = Field("system", description="来源角色")
    topic: str = Field("", description="主题标签")


class MemorySearchRequest(BaseModel):
    """搜索记忆请求。"""

    query: str = Field(..., min_length=1, description="搜索查询")
    n_results: int = Field(5, ge=1, le=50, description="返回条数")
    topic: str | None = Field(None, description="按主题筛选")
    role: str | None = Field(None, description="按角色筛选")


class MemoryItem(BaseModel):
    """记忆条目。"""

    id: str
    content: str
    metadata: dict[str, Any] = {}
    score: float | None = None


class MultiAgentRequest(BaseModel):
    """多 Agent 协作请求。"""

    task: str = Field(..., min_length=1, description="任务描述")
    mode: str = Field("orchestrator", description="协作模式: orchestrator/pipeline/round_robin")
    agent_configs: list[dict[str, str]] | None = Field(
        None, description="子 Agent 配置列表 [{name, system_prompt}]"
    )


class MultiAgentResponse(BaseModel):
    """多 Agent 协作响应。"""

    task_id: str
    mode: str
    output: str
    status: str
    metadata: dict[str, Any] = {}


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: str = "ok"
    version: str = ""
    llm_ready: bool = False
    memory_ready: bool = False
    tools_count: int = 0
    active_sessions: int = 0


# ---------------------------------------------------------------------------
# FastAPI 应用
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    _init_default_components()
    logger.info("JinshiAgent Server 已启动")
    yield
    logger.info("JinshiAgent Server 已关闭")


app = FastAPI(
    title="JinshiAgent API",
    description="AI Agent 工具框架 — HTTP API 接口",
    version="0.5.1",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# 健康检查
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """健康检查接口。"""
    from jinshiagent import __version__

    return HealthResponse(
        status="ok",
        version=__version__,
        llm_ready=_llm_client is not None,
        memory_ready=_default_memory is not None,
        tools_count=len(_tool_registry) if _tool_registry else 0,
        active_sessions=len(_agent_pool),
    )


# ---------------------------------------------------------------------------
# 对话接口
# ---------------------------------------------------------------------------


@app.post("/chat", response_model=ChatResponse, tags=["对话"])
async def chat(
    req: ChatRequest,
    authorization: str | None = Header(None),
):
    """与 Agent 进行对话交互。

    支持多轮对话：传入 session_id 可继续之前的对话，不传则创建新会话。
    """
    _verify_api_key(authorization)

    if not _llm_client:
        raise HTTPException(status_code=503, detail="LLM 服务未配置，请设置 OPENAI_API_KEY")

    # 获取或创建 Agent
    if req.session_id and req.session_id in _agent_pool:
        agent = _agent_pool[req.session_id]
    else:
        session_id = req.session_id or str(uuid.uuid4())[:8]
        agent = Agent(
            name=f"agent-{session_id}",
            llm_client=_llm_client,
            tool_registry=_tool_registry or ToolRegistry(),
            long_term_memory=_default_memory,
            system_prompt=req.system_prompt or "你是一个有用的 AI 助手。",
        )
        _agent_pool[session_id] = agent
        req.session_id = session_id

    # 执行对话
    try:
        response_text = agent.run(req.message)
    except Exception as e:
        logger.error("对话执行失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"对话执行失败: {e}") from e

    # 记录工具调用
    tool_calls_record = []
    for msg in agent.history:
        if msg.role == "tool":
            tool_calls_record.append({
                "role": "tool",
                "content": (msg.content or "")[:200],
            })

    return ChatResponse(
        session_id=req.session_id,
        response=response_text,
        tool_calls=tool_calls_record[-5:],  # 最近5次工具调用
        history_length=len(agent.history),
    )


@app.get("/chat/sessions", response_model=list[SessionResponse], tags=["对话"])
async def list_sessions(authorization: str | None = Header(None)):
    """列出所有活跃的对话会话。"""
    _verify_api_key(authorization)

    sessions = []
    for sid, agent in _agent_pool.items():
        sessions.append(
            SessionResponse(
                session_id=sid,
                agent_name=agent.name,
                history_length=len(agent.history),
                has_long_term_memory=agent.long_term_memory is not None,
            )
        )
    return sessions


@app.get("/chat/sessions/{session_id}/history", tags=["对话"])
async def get_session_history(
    session_id: str,
    authorization: str | None = Header(None),
):
    """获取指定会话的对话历史。"""
    _verify_api_key(authorization)

    if session_id not in _agent_pool:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")

    agent = _agent_pool[session_id]
    return {
        "session_id": session_id,
        "history": [
            {"role": msg.role, "content": msg.content}
            for msg in agent.history
        ],
    }


@app.delete("/chat/sessions/{session_id}", tags=["对话"])
async def delete_session(
    session_id: str,
    authorization: str | None = Header(None),
):
    """删除指定会话。"""
    _verify_api_key(authorization)

    if session_id not in _agent_pool:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")

    del _agent_pool[session_id]
    return {"status": "ok", "message": f"会话 {session_id} 已删除"}


@app.post("/chat/sessions/{session_id}/reset", tags=["对话"])
async def reset_session(
    session_id: str,
    authorization: str | None = Header(None),
):
    """重置指定会话的对话历史。"""
    _verify_api_key(authorization)

    if session_id not in _agent_pool:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")

    agent = _agent_pool[session_id]
    agent.reset()
    return {"status": "ok", "message": f"会话 {session_id} 已重置"}


# ---------------------------------------------------------------------------
# 工具接口
# ---------------------------------------------------------------------------


@app.get("/tools", response_model=list[ToolInfo], tags=["工具"])
async def list_tools(authorization: str | None = Header(None)):
    """列出所有已注册的工具。"""
    _verify_api_key(authorization)

    if not _tool_registry:
        return []

    tools = []
    for name in _tool_registry.list_tools():
        td = _tool_registry.get_tool(name)
        tools.append(
            ToolInfo(
                name=td.name,
                description=td.description,
                parameters=td.parameters,
            )
        )
    return tools


@app.post("/tools/call", response_model=ToolCallResponse, tags=["工具"])
async def call_tool(
    req: ToolCallRequest,
    authorization: str | None = Header(None),
):
    """直接调用指定工具。"""
    _verify_api_key(authorization)

    if not _tool_registry:
        raise HTTPException(status_code=503, detail="工具注册中心未初始化")

    if req.name not in _tool_registry:
        raise HTTPException(status_code=404, detail=f"工具 '{req.name}' 不存在")

    try:
        result = _tool_registry.call(req.name, **req.arguments)
        return ToolCallResponse(name=req.name, result=str(result), success=True)
    except Exception as e:
        return ToolCallResponse(name=req.name, result=str(e), success=False)


# ---------------------------------------------------------------------------
# 记忆接口
# ---------------------------------------------------------------------------


@app.get("/memory/count", tags=["记忆"])
async def memory_count(authorization: str | None = Header(None)):
    """获取长期记忆条数。"""
    _verify_api_key(authorization)

    if not _default_memory:
        raise HTTPException(status_code=503, detail="长期记忆服务未配置")

    return {"count": _default_memory.count(), "backend": _default_memory.backend}


@app.post("/memory/add", tags=["记忆"])
async def memory_add(
    req: MemoryAddRequest,
    authorization: str | None = Header(None),
):
    """添加一条长期记忆。"""
    _verify_api_key(authorization)

    if not _default_memory:
        raise HTTPException(status_code=503, detail="长期记忆服务未配置")

    mem_id = _default_memory.add(req.content, role=req.role, topic=req.topic)
    return {"status": "ok", "memory_id": mem_id}


@app.post("/memory/search", response_model=list[MemoryItem], tags=["记忆"])
async def memory_search(
    req: MemorySearchRequest,
    authorization: str | None = Header(None),
):
    """语义搜索长期记忆。"""
    _verify_api_key(authorization)

    if not _default_memory:
        raise HTTPException(status_code=503, detail="长期记忆服务未配置")

    results = _default_memory.search(
        req.query,
        n_results=req.n_results,
        topic=req.topic,
        role=req.role,
    )
    return [
        MemoryItem(id=r["id"], content=r["content"], metadata=r["metadata"], score=r.get("score"))
        for r in results
    ]


@app.get("/memory/all", response_model=list[MemoryItem], tags=["记忆"])
async def memory_get_all(
    topic: str | None = Query(None),
    role: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    authorization: str | None = Header(None),
):
    """获取所有长期记忆（可按条件过滤）。"""
    _verify_api_key(authorization)

    if not _default_memory:
        raise HTTPException(status_code=503, detail="长期记忆服务未配置")

    results = _default_memory.get_all(topic=topic, role=role, limit=limit)
    return [
        MemoryItem(id=r["id"], content=r["content"], metadata=r["metadata"])
        for r in results
    ]


@app.delete("/memory/{memory_id}", tags=["记忆"])
async def memory_delete(
    memory_id: str,
    authorization: str | None = Header(None),
):
    """删除指定 ID 的长期记忆。"""
    _verify_api_key(authorization)

    if not _default_memory:
        raise HTTPException(status_code=503, detail="长期记忆服务未配置")

    success = _default_memory.delete(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"记忆 {memory_id} 删除失败")
    return {"status": "ok", "message": f"记忆 {memory_id} 已删除"}


# ---------------------------------------------------------------------------
# 多 Agent 协作接口
# ---------------------------------------------------------------------------


@app.post("/multi-agent/run", response_model=MultiAgentResponse, tags=["多Agent"])
async def multi_agent_run(
    req: MultiAgentRequest,
    authorization: str | None = Header(None),
):
    """执行多 Agent 协作任务。

    支持三种协作模式：
    - orchestrator: 主从模式，主 Agent 拆解任务分配给子 Agent
    - pipeline: 流水线模式，多个 Agent 顺序执行
    - round_robin: 轮询模式，每个 Agent 依次补充处理
    """
    _verify_api_key(authorization)

    if not _llm_client:
        raise HTTPException(status_code=503, detail="LLM 服务未配置")

    # 构建子 Agent
    agents: list[Agent] = []
    if req.agent_configs:
        for cfg in req.agent_configs:
            agent = Agent(
                name=cfg.get("name", f"sub-{len(agents)}"),
                llm_client=_llm_client,
                tool_registry=_tool_registry or ToolRegistry(),
                system_prompt=cfg.get("system_prompt", "你是一个 AI 助手。"),
            )
            agents.append(agent)
    else:
        # 默认两个子 Agent
        agents = [
            Agent(
                name="researcher",
                llm_client=_llm_client,
                system_prompt="你负责调研和分析问题。",
            ),
            Agent(
                name="writer",
                llm_client=_llm_client,
                system_prompt="你负责撰写和总结内容。",
            ),
        ]

    # 主 Agent
    master = Agent(
        name="coordinator",
        llm_client=_llm_client,
        tool_registry=_tool_registry or ToolRegistry(),
        system_prompt="你是任务协调者，负责分配和汇总结果。",
    )

    # 选择模式
    mode_map = {
        "orchestrator": TeamMode.ORCHESTRATOR,
        "pipeline": TeamMode.PIPELINE,
        "round_robin": TeamMode.ROUND_ROBIN,
    }
    team_mode = mode_map.get(req.mode, TeamMode.ORCHESTRATOR)

    # 构建团队
    team = AgentTeam(name="api_team", mode=team_mode, master=master)
    for a in agents:
        team.add_member(a)

    # 执行
    task_id = str(uuid.uuid4())[:8]
    try:
        result = team.run(req.task)
        return MultiAgentResponse(
            task_id=task_id,
            mode=req.mode,
            output=result.output,
            status=result.status.value,
            metadata=result.metadata,
        )
    except Exception as e:
        logger.error("多 Agent 执行失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"多 Agent 执行失败: {e}") from e


@app.get("/multi-agent/modes", tags=["多Agent"])
async def list_multi_agent_modes(authorization: str | None = Header(None)):
    """列出支持的多 Agent 协作模式。"""
    _verify_api_key(authorization)
    return {
        "modes": [
            {
                "name": "orchestrator",
                "description": "主从模式 — 主 Agent 拆解任务，分配给子 Agent 执行，汇总结果",
            },
            {
                "name": "pipeline",
                "description": "流水线模式 — 多个 Agent 顺序执行，前一个的输出是后一个的输入",
            },
            {
                "name": "round_robin",
                "description": "轮询模式 — 每个 Agent 依次对同一任务进行补充处理",
            },
        ]
    }


# ---------------------------------------------------------------------------
# 内容创作接口
# ---------------------------------------------------------------------------


class CreationBundleRequest(BaseModel):
    """一键生成全套创作素材请求。"""

    topic: str = Field(..., min_length=1, description="创作主题")
    platform: str = Field(..., description="目标平台: xiaohongshu/douyin/kuaishou/bilibili/zhihu/toutiao/weibo/wechat")
    extra_requirements: str = Field("", description="额外要求")


class CreationTopicRequest(BaseModel):
    """批量选题请求。"""

    niche: str = Field(..., min_length=1, description="创作领域/赛道")
    platform: str = Field(..., description="目标平台")
    count: int = Field(5, ge=1, le=20, description="选题数量")


class CreationSingleRequest(BaseModel):
    """单项生成请求。"""

    topic: str = Field(..., min_length=1, description="创作主题")
    platform: str = Field(..., description="目标平台")
    template_type: str = Field(..., description="生成类型: title/script/voice_over/storyboard/hook/copywriting/tags/cover")
    extra_requirements: str = Field("", description="额外要求")


class CreationMultiPlatformRequest(BaseModel):
    """多平台适配请求。"""

    topic: str = Field(..., min_length=1, description="创作主题")
    platforms: list[str] | None = Field(None, description="目标平台列表（默认全部）")
    extra_requirements: str = Field("", description="额外要求")


@app.get("/creation/platforms", tags=["创作"])
async def creation_list_platforms(authorization: str | None = Header(None)):
    """列出所有支持的自媒体平台。"""
    _verify_api_key(authorization)

    from jinshiagent.creation.templates import list_platforms
    return {"platforms": list_platforms()}


@app.post("/creation/bundle", tags=["创作"])
async def creation_bundle(
    req: CreationBundleRequest,
    authorization: str | None = Header(None),
):
    """一键生成全套创作素材（标题+脚本/文案+标签+封面）。

    根据目标平台的风格规范，一次性生成完整的短视频/图文创作素材。
    """
    _verify_api_key(authorization)

    if not _llm_client:
        raise HTTPException(status_code=503, detail="LLM 服务未配置，请设置 OPENAI_API_KEY")

    from jinshiagent.creation.generator import ContentGenerator

    gen = ContentGenerator(llm_client=_llm_client)
    try:
        result = gen.generate_bundle(
            topic=req.topic,
            platform=req.platform,
            extra_requirements=req.extra_requirements,
        )
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("创作生成失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成失败: {e}") from e


@app.post("/creation/topics", tags=["创作"])
async def creation_topics(
    req: CreationTopicRequest,
    authorization: str | None = Header(None),
):
    """批量产出选题方向。

    根据创作赛道和目标平台，生成多个差异化的选题方向。
    """
    _verify_api_key(authorization)

    if not _llm_client:
        raise HTTPException(status_code=503, detail="LLM 服务未配置")

    from jinshiagent.creation.generator import ContentGenerator

    gen = ContentGenerator(llm_client=_llm_client)
    try:
        result = gen.generate_topics(
            niche=req.niche,
            platform=req.platform,
            count=req.count,
        )
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("选题生成失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成失败: {e}") from e


@app.post("/creation/single", tags=["创作"])
async def creation_single(
    req: CreationSingleRequest,
    authorization: str | None = Header(None),
):
    """单项生成（仅标题/仅脚本/仅标签等）。

    template_type 可选值: title, script, voice_over, storyboard, hook, copywriting, tags, cover
    """
    _verify_api_key(authorization)

    if not _llm_client:
        raise HTTPException(status_code=503, detail="LLM 服务未配置")

    from jinshiagent.creation.generator import ContentGenerator
    from jinshiagent.creation.templates import TemplateType

    type_map = {
        "title": TemplateType.TITLE,
        "script": TemplateType.SCRIPT,
        "voice_over": TemplateType.VOICE_OVER,
        "storyboard": TemplateType.STORYBOARD,
        "hook": TemplateType.HOOK,
        "copywriting": TemplateType.COPYWRITING,
        "tags": TemplateType.TAGS,
        "cover": TemplateType.COVER,
    }
    template_type = type_map.get(req.template_type)
    if not template_type:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的类型: {req.template_type}，可选: {list(type_map.keys())}",
        )

    gen = ContentGenerator(llm_client=_llm_client)
    try:
        result = gen.generate_single(
            topic=req.topic,
            platform=req.platform,
            template_type=template_type,
            extra_requirements=req.extra_requirements,
        )
        return {"content": result, "platform": req.platform, "type": req.template_type}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("单项生成失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成失败: {e}") from e


@app.post("/creation/multi-platform", tags=["创作"])
async def creation_multi_platform(
    req: CreationMultiPlatformRequest,
    authorization: str | None = Header(None),
):
    """同一主题适配多平台。

    同一创作主题，自动适配多个自媒体平台的内容风格。
    """
    _verify_api_key(authorization)

    if not _llm_client:
        raise HTTPException(status_code=503, detail="LLM 服务未配置")

    from jinshiagent.creation.generator import ContentGenerator

    gen = ContentGenerator(llm_client=_llm_client)
    try:
        results = gen.generate_multi_platform(
            topic=req.topic,
            platforms=req.platforms,
            extra_requirements=req.extra_requirements,
        )
        return {"topic": req.topic, "bundles": [r.model_dump() for r in results]}
    except Exception as e:
        logger.error("多平台生成失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成失败: {e}") from e


# ---------------------------------------------------------------------------
# 启动入口
# ---------------------------------------------------------------------------


def main() -> None:
    """启动 FastAPI 服务。"""
    import uvicorn

    host = os.getenv("JINSHI_HOST", "0.0.0.0")
    port = int(os.getenv("JINSHI_PORT", "8000"))

    uvicorn.run(
        "jinshiagent.server:app",
        host=host,
        port=port,
        reload=os.getenv("JINSHI_RELOAD", "0") == "1",
        log_level="info",
    )


if __name__ == "__main__":
    main()
