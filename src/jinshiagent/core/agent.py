"""Agent 基类 — 统一智能体生命周期管理

所有自定义 Agent 均应继承此类。内置 ReAct 循环支持：
  Think → Act (工具调用) → Observe (结果反馈) → ... → 最终回答

使用示例::

    from jinshiagent.llm import LLMClient, LLMConfig
    from jinshiagent.core.tool_registry import ToolRegistry

    class MyAgent(Agent):
        pass  # 使用继承的 ReAct run()

    llm = LLMClient(LLMConfig(api_key="sk-xxx"))
    registry = ToolRegistry()

    @registry.register
    def search(query: str) -> str:
        \"\"搜索\"\""
        return f"结果: {query}"

    agent = MyAgent(
        name="demo",
        llm_client=llm,
        tool_registry=registry,
        system_prompt="你是一个有用的助手。",
    )
    answer = agent.run("请搜索一下 Agent 是什么")
    print(answer)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from jinshiagent.core.message import Message
from jinshiagent.core.tool_registry import ToolRegistry
from jinshiagent.utils.exceptions import AgentError, ToolError

logger = logging.getLogger("jinshiagent.core.agent")


class Agent:
    """Agent 基类，提供生命周期管理与 ReAct 推理循环。

    ReAct 循环流程：
      1. 将用户输入加入历史
      2. 调用 LLM，传入工具 schema
      3. 若 LLM 返回 tool_calls：执行工具 → 将结果加入消息 → 回到步骤 2
      4. 若 LLM 返回最终回答：记录到历史并返回

    Attributes:
        name: Agent 唯一标识名
        description: Agent 功能描述
        system_prompt: 系统提示词（每次 LLM 调用前置）
        llm_client: LLMClient 实例（ReAct 循环必需）
        tool_registry: 工具注册中心实例
        history: 对话历史 Message 列表
        max_iterations: 单次 run() 最大推理迭代次数
    """

    def __init__(
        self,
        name: str | None = None,
        description: str = "",
        system_prompt: str = "",
        llm_client: Any = None,
        tool_registry: ToolRegistry | None = None,
        max_iterations: int = 10,
    ) -> None:
        self.id: str = str(uuid.uuid4())[:8]
        self.name: str = name or f"agent-{self.id}"
        self.description: str = description
        self.system_prompt: str = system_prompt
        self.llm_client: Any = llm_client
        self.tool_registry: ToolRegistry = tool_registry or ToolRegistry()
        self.history: list[Message] = []
        self.max_iterations: int = max_iterations

    # —— 公开 API ————————————————————————————————————————————————————————

    def run(self, user_input: str) -> str:
        """执行 ReAct 推理循环，返回最终回答。

        ReAct 循环：
          迭代 1..N:
            调用 LLM（携带工具 schema）
            → 若有 tool_calls: 执行工具，将结果追加到消息，继续迭代
            → 若无非工具调用: 返回 content 作为最终回答
          若超过 max_iterations: 返回超时提示

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
        messages: list[dict[str, Any]] = self._build_messages()

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
            return content

        # 5. 超过最大迭代次数
        logger.warning("[ReAct] 达到最大迭代次数 %d，强制结束", self.max_iterations)
        fallback = "抱歉，我的思考步骤超过了限制，无法完整回答这个问题。"
        self.add_message("assistant", fallback)
        return fallback

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

    # —— 内部方法 —————————————————————————————————————————————————————————

    def _build_messages(self) -> list[dict[str, Any]]:
        """将 self.history 转为 OpenAI 格式消息列表，前置 system_prompt。"""
        messages: list[dict[str, Any]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        for msg in self.history:
            messages.append(msg.to_openai_format())
        return messages

    def __repr__(self) -> str:
        return (
            f"Agent(name={self.name!r},"
            f" tools={len(self.tool_registry)},"
            f" history={len(self.history)})"
        )
