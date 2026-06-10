"""Agent 基类 — 统一智能体生命周期管理

所有自定义 Agent 均应继承此类。内置 ReAct 循环支持：
  Think → Act (工具调用) → Observe (结果反馈) → ... → 最终回答

支持同步和异步两种运行模式：
  - run(): 同步 ReAct 循环
  - arun(): 异步 ReAct 循环（需 async/await）

支持短期和长期记忆：
  - history: 对话历史（短期记忆）
  - long_term_memory: ChromaDB 向量检索（长期记忆，可选）

使用示例::

    from jinshiagent.llm import LLMClient, LLMConfig
    from jinshiagent.core.tool_registry import ToolRegistry
    from jinshiagent.memory import LongTermMemory

    class MyAgent(Agent):
        pass  # 使用继承的 ReAct run()

    llm = LLMClient(LLMConfig(api_key="sk-xxx"))
    registry = ToolRegistry()

    @registry.register
    def search(query: str) -> str:
        \"\"搜索\"\"\"
        return f"结果: {query}"

    # 带长期记忆的 Agent
    ltm = LongTermMemory(collection_name="my_agent")
    agent = MyAgent(
        name="demo",
        llm_client=llm,
        tool_registry=registry,
        system_prompt="你是一个有用的助手。",
        long_term_memory=ltm,
    )
    answer = agent.run("请搜索一下 Agent 是什么")
    print(answer)
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from jinshiagent.core.message import Message
from jinshiagent.core.tool_registry import ToolRegistry
from jinshiagent.utils.exceptions import AgentError, ToolError

if TYPE_CHECKING:
    from jinshiagent.memory.long_term import LongTermMemory

logger = logging.getLogger("jinshiagent.core.agent")


class Agent:
    """Agent 基类，提供生命周期管理与 ReAct 推理循环。

    ReAct 循环流程：
      1. 将用户输入加入历史
      2. （可选）从长期记忆检索相关上下文，注入到 system prompt
      3. 调用 LLM，传入工具 schema
      4. 若 LLM 返回 tool_calls：执行工具 → 将结果加入消息 → 回到步骤 3
      5. 若 LLM 返回最终回答：记录到历史并返回

    Attributes:
        name: Agent 唯一标识名
        description: Agent 功能描述
        system_prompt: 系统提示词（每次 LLM 调用前置）
        llm_client: LLMClient 实例（ReAct 循环必需）
        tool_registry: 工具注册中心实例
        history: 对话历史 Message 列表（短期记忆）
        long_term_memory: ChromaDB 长期记忆实例（可选）
        max_iterations: 单次 run() 最大推理迭代次数
    """

    def __init__(
        self,
        name: str | None = None,
        description: str = "",
        system_prompt: str = "",
        llm_client: Any = None,
        tool_registry: ToolRegistry | None = None,
        long_term_memory: LongTermMemory | None = None,
        max_iterations: int = 10,
    ) -> None:
        self.id: str = str(uuid.uuid4())[:8]
        self.name: str = name or f"agent-{self.id}"
        self.description: str = description
        self.system_prompt: str = system_prompt
        self.llm_client: Any = llm_client
        self.tool_registry: ToolRegistry = tool_registry or ToolRegistry()
        self.long_term_memory: LongTermMemory | None = long_term_memory
        self.history: list[Message] = []
        self.max_iterations: int = max_iterations

    # —— 同步 ReAct 循环 ————————————————————————————————————————————————

    def run(self, user_input: str) -> str:
        """执行同步 ReAct 推理循环，返回最终回答。

        ReAct 循环：
          迭代 1..N:
            调用 LLM（携带工具 schema）
            → 若有 tool_calls: 执行工具，将结果追加到消息，继续迭代
            → 若无非工具调用: 返回 content 作为最终回答
          若超过 max_iterations: 返回超时提示

        如果配置了 long_term_memory，会自动：
          1. 检索与用户输入相关的长期记忆，注入到 system prompt
          2. 将本轮对话的关键信息存入长期记忆

        Args:
            user_input: 用户输入文本

        Returns:
            Agent 的最终回答文本

        Raises:
            AgentError: llm_client 未配置，或循环异常中断
        """
        if self.llm_client is None:
            raise AgentError(
                "llm_client 未配置，ReAct 循环无法执行。",
                details="请在构造 Agent 时传入 llm_client=LLMClient(...)",
            )

        # 1. 记录用户输入
        self.add_message("user", user_input)
        logger.info("[ReAct] 开始 | agent=%s | 输入=%r", self.name, user_input)

        # 2. 构建初始消息列表（system + 历史）
        #    如果有长期记忆，注入相关上下文
        system_prompt = self.system_prompt
        if self.long_term_memory:
            try:
                context = self.long_term_memory.get_relevant_context(user_input)
                if context:
                    system_prompt = (
                        f"{self.system_prompt}\n\n"
                        f"## 相关记忆\n{context}"
                    )
                    logger.debug("[ReAct] 注入长期记忆上下文: %d 字符", len(context))
            except Exception as e:
                logger.warning("[ReAct] 长期记忆检索失败: %s", e)

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        for msg in self.history:
            messages.append(msg.to_openai_format())

        # 3. 获取工具 schemas（若注册了工具）
        tools: list[dict[str, Any]] | None = None
        if self.tool_registry:
            tools = self.tool_registry.get_all_schemas()
            logger.debug("[ReAct] 已注册工具: %s", self.tool_registry.list_tools())

        # 4. ReAct 循环
        for step in range(1, self.max_iterations + 1):
            logger.info("[ReAct] 迭代 %d/%d", step, self.max_iterations)

            # 4a. 调用 LLM
            try:
                response_msg: dict[str, Any] = self.llm_client.chat_with_tools(
                    messages=messages, tools=tools
                )
            except Exception as e:
                raise AgentError(
                    f"LLM 调用失败（迭代 {step}）: {e}",
                    details=f"messages 条数: {len(messages)}",
                ) from e

            role: str = response_msg.get("role", "assistant")
            logger.debug("[ReAct] LLM 响应: role=%s", role)

            # 4b. 检查是否需要调用工具
            if response_msg.get("tool_calls"):
                # 将 LLM 的助手消息（含 tool_calls）加入上下文
                messages.append({
                    "role": response_msg["role"],
                    "content": response_msg.get("content"),
                    "tool_calls": response_msg["tool_calls"],
                })

                # 执行每个 tool_call
                for tc in response_msg["tool_calls"]:
                    try:
                        tool_result: dict[str, str] = self.tool_registry.execute_tool_call(tc)
                        messages.append(tool_result)
                        logger.info(
                            "[ReAct] 工具执行: %s → %r",
                            tc["function"]["name"],
                            (tool_result.get("content") or "")[:100],
                        )
                    except ToolError:
                        # 工具执行失败，将错误信息作为 tool 消息返回给 LLM
                        logger.warning(
                            "[ReAct] 工具执行失败: %s",
                            tc["function"]["name"],
                            exc_info=True,
                        )
                        messages.append({
                            "tool_call_id": tc["id"],
                            "role": "tool",
                            "name": tc["function"]["name"],
                            "content": f"工具执行失败: {tc['function']['name']}",
                        })
                # 继续下一轮迭代（让 LLM 根据工具结果继续推理）
                continue

            # 4c. LLM 返回了最终回答（无 tool_calls）
            content: str = response_msg.get("content") or ""
            self.add_message("assistant", content)
            logger.info("[ReAct] 完成 | 共 %d 次迭代 | 回答=%r", step, content[:80])

            # 5. 将本轮关键信息存入长期记忆
            self._persist_to_long_term(user_input, content)

            return content

        # 6. 超过最大迭代次数
        logger.warning("[ReAct] 达到最大迭代次数 %d，强制结束", self.max_iterations)
        fallback = "抱歉，我的思考步骤超过了限制，无法完整回答这个问题。"
        self.add_message("assistant", fallback)
        self._persist_to_long_term(user_input, fallback)
        return fallback

    # —— 异步 ReAct 循环 ————————————————————————————————————————————————

    async def arun(self, user_input: str) -> str:
        """执行异步 ReAct 推理循环，返回最终回答。

        与 run() 相同的逻辑，但使用异步 LLM 调用和工具执行，
        适合 I/O 密集型场景（网络请求、并发工具调用）。

        要求:
            - llm_client 需实现 achat_with_tools() 异步方法
            - 异步工具函数需以 _async 后缀注册或使用 async_tool 装饰器

        Args:
            user_input: 用户输入文本

        Returns:
            Agent 的最终回答文本

        Raises:
            AgentError: llm_client 未配置，或循环异常中断
        """
        if self.llm_client is None:
            raise AgentError(
                "llm_client 未配置，异步 ReAct 循环无法执行。",
                details="请在构造 Agent 时传入 llm_client=LLMClient(...)",
            )

        # 1. 记录用户输入
        self.add_message("user", user_input)
        logger.info("[Async ReAct] 开始 | agent=%s | 输入=%r", self.name, user_input)

        # 2. 构建消息列表（含长期记忆上下文）
        system_prompt = self.system_prompt
        if self.long_term_memory:
            try:
                context = self.long_term_memory.get_relevant_context(user_input)
                if context:
                    system_prompt = (
                        f"{self.system_prompt}\n\n"
                        f"## 相关记忆\n{context}"
                    )
                    logger.debug("[Async ReAct] 注入长期记忆上下文: %d 字符", len(context))
            except Exception as e:
                logger.warning("[Async ReAct] 长期记忆检索失败: %s", e)

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        for msg in self.history:
            messages.append(msg.to_openai_format())

        # 3. 获取工具 schemas
        tools: list[dict[str, Any]] | None = None
        if self.tool_registry:
            tools = self.tool_registry.get_all_schemas()

        # 4. 异步 ReAct 循环
        for step in range(1, self.max_iterations + 1):
            logger.info("[Async ReAct] 迭代 %d/%d", step, self.max_iterations)

            # 4a. 异步调用 LLM
            try:
                if hasattr(self.llm_client, "achat_with_tools"):
                    response_msg = await self.llm_client.achat_with_tools(
                        messages=messages, tools=tools
                    )
                elif hasattr(self.llm_client, "chat_with_tools"):
                    # 降级到同步调用
                    response_msg = self.llm_client.chat_with_tools(
                        messages=messages, tools=tools
                    )
                else:
                    raise AgentError("llm_client 不支持任何调用方法")
            except AgentError:
                raise
            except Exception as e:
                raise AgentError(
                    f"异步 LLM 调用失败（迭代 {step}）: {e}",
                    details=f"messages 条数: {len(messages)}",
                ) from e

            # 4b. 检查是否需要调用工具
            if response_msg.get("tool_calls"):
                messages.append({
                    "role": response_msg["role"],
                    "content": response_msg.get("content"),
                    "tool_calls": response_msg["tool_calls"],
                })

                # 执行工具（异步优先，降级同步）
                for tc in response_msg["tool_calls"]:
                    try:
                        tool_result = await self._aexecute_tool_call(tc)
                        messages.append(tool_result)
                        logger.info(
                            "[Async ReAct] 工具执行: %s → %r",
                            tc["function"]["name"],
                            (tool_result.get("content") or "")[:100],
                        )
                    except ToolError:
                        logger.warning(
                            "[Async ReAct] 工具执行失败: %s",
                            tc["function"]["name"],
                            exc_info=True,
                        )
                        messages.append({
                            "tool_call_id": tc["id"],
                            "role": "tool",
                            "name": tc["function"]["name"],
                            "content": f"工具执行失败: {tc['function']['name']}",
                        })
                continue

            # 4c. 最终回答
            content: str = response_msg.get("content") or ""
            self.add_message("assistant", content)
            logger.info(
                "[Async ReAct] 完成 | 共 %d 次迭代 | 回答=%r", step, content[:80]
            )

            # 5. 存入长期记忆
            self._persist_to_long_term(user_input, content)
            return content

        # 6. 超时
        logger.warning("[Async ReAct] 达到最大迭代次数 %d，强制结束", self.max_iterations)
        fallback = "抱歉，我的思考步骤超过了限制，无法完整回答这个问题。"
        self.add_message("assistant", fallback)
        self._persist_to_long_term(user_input, fallback)
        return fallback

    async def _aexecute_tool_call(self, tool_call: dict) -> dict[str, str]:
        """异步执行工具调用。

        优先使用异步工具函数，降级到同步工具函数。
        """
        import asyncio
        import json

        func_name: str = tool_call["function"]["name"]
        raw_args: str = tool_call["function"]["arguments"]
        kwargs: dict[str, Any] = json.loads(raw_args) if raw_args else {}

        if func_name not in self.tool_registry._tools:
            raise KeyError(f"工具 '{func_name}' 未注册")

        tool_def = self.tool_registry._tools[func_name]
        func = tool_def.func

        # 如果是异步函数，直接 await
        if asyncio.iscoroutinefunction(func):
            result = await func(**kwargs)
        else:
            # 同步函数在事件循环中执行
            result = func(**kwargs)

        return {
            "tool_call_id": tool_call["id"],
            "role": "tool",
            "name": func_name,
            "content": str(result),
        }

    # —— 公开 API ————————————————————————————————————————————————————————

    def add_message(self, role: str, content: str, **metadata: Any) -> Message:
        """添加一条消息到对话历史。

        Args:
            role: 消息角色 (user / assistant / tool / system)
            content: 消息内容
            **metadata: 附加元数据

        Returns:
            创建的 Message 对象
        """
        msg = Message(role=role, content=content, metadata=metadata)
        self.history.append(msg)
        return msg

    def reset(self) -> None:
        """重置 Agent 状态，清空对话历史。"""
        self.history.clear()
        logger.debug("[ReAct] Agent %s 已重置对话历史", self.name)

    def register_tool(self, func: Any) -> Any:
        """注册一个工具函数（装饰器语法）。

        用法::

            agent = Agent(name="demo")
            @agent.register_tool
            def search(query: str) -> str:
                return f"搜索结果: {query}"
        """
        return self.tool_registry.register(func)

    def remember(self, content: str, *, topic: str = "", role: str = "system") -> str | None:
        """手动将信息存入长期记忆。

        Args:
            content: 要记忆的内容
            topic: 主题标签
            role: 来源角色

        Returns:
            记忆 ID（如果没有配置长期记忆则返回 None）
        """
        if self.long_term_memory is None:
            logger.warning("未配置长期记忆，无法存储: %r", content[:50])
            return None
        return self.long_term_memory.add(content, role=role, topic=topic)

    def recall(self, query: str, *, n_results: int = 5) -> list[dict[str, Any]]:
        """从长期记忆中检索相关信息。

        Args:
            query: 搜索查询
            n_results: 返回条数

        Returns:
            匹配的记忆列表
        """
        if self.long_term_memory is None:
            logger.warning("未配置长期记忆，无法检索")
            return []
        return self.long_term_memory.search(query, n_results=n_results)

    # —— 内部方法 —————————————————————————————————————————————————————————

    def _build_messages(self) -> list[dict[str, Any]]:
        """将 self.history 转为 OpenAI 格式消息列表，前置 system_prompt。"""
        messages: list[dict[str, Any]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        for msg in self.history:
            messages.append(msg.to_openai_format())
        return messages

    def _persist_to_long_term(self, user_input: str, assistant_response: str) -> None:
        """将本轮对话的关键信息存入长期记忆。"""
        if self.long_term_memory is None:
            return
        try:
            # 存储用户输入
            self.long_term_memory.add(
                user_input,
                role="user",
                topic="conversation",
                metadata={"agent": self.name},
            )
            # 存储助手回答
            self.long_term_memory.add(
                assistant_response,
                role="assistant",
                topic="conversation",
                metadata={"agent": self.name},
            )
            logger.debug("[ReAct] 对话已存入长期记忆")
        except Exception as e:
            logger.warning("[ReAct] 长期记忆存储失败: %s", e)

    def __repr__(self) -> str:
        ltm_status = "enabled" if self.long_term_memory else "disabled"
        return (
            f"Agent(name={self.name!r},"
            f" tools={len(self.tool_registry)},"
            f" history={len(self.history)},"
            f" long_term_memory={ltm_status})"
        )
