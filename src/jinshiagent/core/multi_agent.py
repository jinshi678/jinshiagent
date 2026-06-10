"""多 Agent 协作框架 — 主从调度、任务拆解与结果汇总

提供三种协作模式：
    - Orchestrator: 主从模式，主 Agent 负责任务拆解、分配和汇总
    - Pipeline: 流水线模式，多个 Agent 顺序执行，前一个的输出是后一个的输入
    - RoundRobin: 轮询模式，多个 Agent 依次对同一任务进行补充处理

核心类:
    - SubAgent: 子 Agent 定义（名称、描述、能力、实例）
    - TaskResult: 任务执行结果（状态、输出、来源）
    - Orchestrator: 主从调度器
    - Pipeline: 流水线调度器
    - AgentTeam: 多模式协作团队

使用示例::

    from jinshiagent.core.agent import Agent
    from jinshiagent.core.multi_agent import Orchestrator, SubAgent

    # 创建主 Agent 和子 Agent
    master = Agent(name="coordinator", system_prompt="你是任务协调者")
    weather_agent = Agent(name="weather", system_prompt="你负责查天气")
    writer_agent = Agent(name="writer", system_prompt="你负责写建议")

    # 配置编排器
    orch = Orchestrator(
        master_agent=master,
        sub_agents=[
            SubAgent(name="weather", agent=weather_agent, description="查询天气信息"),
            SubAgent(name="writer", agent=writer_agent, description="撰写出行建议"),
        ],
    )

    # 执行多 Agent 任务
    result = orch.run("帮我查北京天气并写一份出行建议")
    print(result.output)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from jinshiagent.core.agent import Agent
from jinshiagent.utils.exceptions import AgentError

logger = logging.getLogger("jinshiagent.core.multi_agent")


# ── 数据模型 ──────────────────────────────────────────────────────────


class TaskStatus(str, Enum):
    """任务状态枚举。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SubAgent:
    """子 Agent 定义。

    Attributes:
        name: 子 Agent 名称（在编排器内唯一）
        agent: Agent 实例
        description: 功能描述（主 Agent 用于判断何时调用此子 Agent）
        tags: 标签列表（用于分类筛选）
    """

    name: str
    agent: Agent
    description: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class TaskResult:
    """单个任务执行结果。

    Attributes:
        task_id: 任务 ID
        agent_name: 执行 Agent 的名称
        status: 任务状态
        output: 执行输出
        error: 错误信息（如有）
        metadata: 附加元数据
    """

    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_name: str = ""
    status: TaskStatus = TaskStatus.PENDING
    output: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    def __repr__(self) -> str:
        return (
            f"TaskResult(id={self.task_id!r}, agent={self.agent_name!r}, "
            f"status={self.status.value}, output={self.output[:50]!r})"
        )


# ── 主从编排器 Orchestrator ──────────────────────────────────────────


class Orchestrator:
    """主从模式编排器 — 主 Agent 拆解任务，分配给子 Agent 执行，汇总结果。

    工作流程：
        1. 用户提交任务给 Orchestrator
        2. 主 Agent 分析任务，决定需要哪些子 Agent 参与
        3. 按依赖顺序调度子 Agent 执行
        4. 汇总所有子 Agent 的结果，由主 Agent 生成最终回答

    如果未配置 LLM（主 Agent 无 llm_client），则使用规则模式：
        按顺序依次调用所有子 Agent，将结果拼接返回。

    Attributes:
        master_agent: 主 Agent 实例
        sub_agents: 子 Agent 列表
        max_retries: 子 Agent 执行失败时的最大重试次数
    """

    def __init__(
        self,
        master_agent: Agent,
        sub_agents: list[SubAgent] | None = None,
        max_retries: int = 1,
    ) -> None:
        self.master_agent = master_agent
        self.sub_agents: dict[str, SubAgent] = {}
        self.max_retries = max_retries
        self._results: list[TaskResult] = []

        if sub_agents:
            for sa in sub_agents:
                self.add_sub_agent(sa)

    def add_sub_agent(self, sub_agent: SubAgent) -> None:
        """添加子 Agent。

        Args:
            sub_agent: 子 Agent 定义

        Raises:
            ValueError: 子 Agent 名称已存在
        """
        if sub_agent.name in self.sub_agents:
            raise ValueError(f"子 Agent '{sub_agent.name}' 已存在")
        self.sub_agents[sub_agent.name] = sub_agent
        logger.info("添加子 Agent: %s (%s)", sub_agent.name, sub_agent.description)

    def remove_sub_agent(self, name: str) -> None:
        """移除子 Agent。"""
        if name not in self.sub_agents:
            raise KeyError(f"子 Agent '{name}' 不存在")
        del self.sub_agents[name]
        logger.info("移除子 Agent: %s", name)

    def run(self, task: str, **kwargs: Any) -> TaskResult:
        """执行主从编排任务（同步）。

        Args:
            task: 用户任务描述
            **kwargs: 附加参数

        Returns:
            最终汇总的 TaskResult
        """
        logger.info("[Orchestrator] 收到任务: %r", task[:100])
        self._results.clear()

        # 1. 主 Agent 拆解任务（如果有 LLM）
        if self.master_agent.llm_client is not None:
            return self._run_with_llm(task, **kwargs)
        else:
            return self._run_rule_based(task, **kwargs)

    async def arun(self, task: str, **kwargs: Any) -> TaskResult:
        """执行主从编排任务（异步）。"""
        logger.info("[Async Orchestrator] 收到任务: %r", task[:100])
        self._results.clear()

        if self.master_agent.llm_client is not None:
            return await self._arun_with_llm(task, **kwargs)
        else:
            return await self._arun_rule_based(task, **kwargs)

    # —— LLM 驱动模式 ————————————————————————————————————————

    def _run_with_llm(self, task: str, **kwargs: Any) -> TaskResult:
        """LLM 驱动：主 Agent 拆解任务并分配给子 Agent。"""
        # 构建任务分配提示
        agent_list = "\n".join(
            f"  - {name}: {sa.description}"
            for name, sa in self.sub_agents.items()
        )
        dispatch_prompt = (
            f"你是一个任务协调者。根据用户的需求，决定需要哪些 Agent 来完成。\n\n"
            f"可用的子 Agent：\n{agent_list}\n\n"
            f"用户任务：{task}\n\n"
            f"请按以下格式输出（每行一个 Agent 调用）：\n"
            f"AGENT: <agent_name>\n"
            f"INPUT: <传递给该 Agent 的具体输入>\n\n"
            f"只输出需要调用的 Agent，按执行顺序排列。"
        )

        # 主 Agent 决定调度计划
        dispatch_result = self.master_agent.run(dispatch_prompt)
        logger.info("[Orchestrator] 调度计划:\n%s", dispatch_result)

        # 解析调度计划
        plan = self._parse_dispatch(dispatch_result)
        logger.info("[Orchestrator] 解析得到 %d 个子任务", len(plan))

        # 执行子任务
        sub_results: list[TaskResult] = []
        for agent_name, sub_input in plan:
            result = self._execute_sub_agent(agent_name, sub_input)
            sub_results.append(result)

        # 汇总结果
        return self._aggregate_results(task, sub_results)

    async def _arun_with_llm(self, task: str, **kwargs: Any) -> TaskResult:
        """LLM 驱动异步版本。"""
        agent_list = "\n".join(
            f"  - {name}: {sa.description}"
            for name, sa in self.sub_agents.items()
        )
        dispatch_prompt = (
            f"你是一个任务协调者。根据用户的需求，决定需要哪些 Agent 来完成。\n\n"
            f"可用的子 Agent：\n{agent_list}\n\n"
            f"用户任务：{task}\n\n"
            f"请按以下格式输出（每行一个 Agent 调用）：\n"
            f"AGENT: <agent_name>\n"
            f"INPUT: <传递给该 Agent 的具体输入>\n\n"
            f"只输出需要调用的 Agent，按执行顺序排列。"
        )

        dispatch_result = await self.master_agent.arun(dispatch_prompt)
        plan = self._parse_dispatch(dispatch_result)

        sub_results: list[TaskResult] = []
        for agent_name, sub_input in plan:
            result = await self._aexecute_sub_agent(agent_name, sub_input)
            sub_results.append(result)

        return await self._aaggregate_results(task, sub_results)

    # —— 规则模式（无 LLM） ———————————————————————————————

    def _run_rule_based(self, task: str, **kwargs: Any) -> TaskResult:
        """规则模式：按顺序依次调用所有子 Agent。"""
        logger.info("[Orchestrator] 使用规则模式，依次调用 %d 个子 Agent", len(self.sub_agents))

        sub_results: list[TaskResult] = []
        context = task  # 前一个 Agent 的输出作为后一个的输入

        for name, sa in self.sub_agents.items():
            result = self._execute_sub_agent(name, context)
            sub_results.append(result)
            if result.is_success:
                context = result.output  # 传递输出给下一个
            else:
                logger.warning("[Orchestrator] 子 Agent %s 失败: %s", name, result.error)

        return self._aggregate_results(task, sub_results)

    async def _arun_rule_based(self, task: str, **kwargs: Any) -> TaskResult:
        """规则模式异步版本。"""
        sub_results: list[TaskResult] = []
        context = task

        for name, sa in self.sub_agents.items():
            result = await self._aexecute_sub_agent(name, context)
            sub_results.append(result)
            if result.is_success:
                context = result.output
            else:
                logger.warning("[Async Orchestrator] 子 Agent %s 失败: %s", name, result.error)

        return await self._aaggregate_results(task, sub_results)

    # —— 子 Agent 执行 ———————————————————————————————

    def _execute_sub_agent(self, agent_name: str, task_input: str) -> TaskResult:
        """执行单个子 Agent（同步，带重试）。"""
        if agent_name not in self.sub_agents:
            return TaskResult(
                agent_name=agent_name,
                status=TaskStatus.FAILED,
                error=f"子 Agent '{agent_name}' 不存在",
            )

        sa = self.sub_agents[agent_name]
        result = TaskResult(agent_name=agent_name, status=TaskStatus.RUNNING)

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    "[Orchestrator] 执行子 Agent %s (第 %d 次)", agent_name, attempt
                )
                output = sa.agent.run(task_input)
                result.output = output
                result.status = TaskStatus.COMPLETED
                self._results.append(result)
                logger.info("[Orchestrator] 子 Agent %s 完成", agent_name)
                return result
            except Exception as e:
                logger.warning(
                    "[Orchestrator] 子 Agent %s 第 %d 次执行失败: %s",
                    agent_name, attempt, e,
                )
                result.error = str(e)

        result.status = TaskStatus.FAILED
        self._results.append(result)
        return result

    async def _aexecute_sub_agent(self, agent_name: str, task_input: str) -> TaskResult:
        """执行单个子 Agent（异步，带重试）。"""
        if agent_name not in self.sub_agents:
            return TaskResult(
                agent_name=agent_name,
                status=TaskStatus.FAILED,
                error=f"子 Agent '{agent_name}' 不存在",
            )

        sa = self.sub_agents[agent_name]
        result = TaskResult(agent_name=agent_name, status=TaskStatus.RUNNING)

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    "[Async Orchestrator] 执行子 Agent %s (第 %d 次)", agent_name, attempt
                )
                output = await sa.agent.arun(task_input)
                result.output = output
                result.status = TaskStatus.COMPLETED
                self._results.append(result)
                return result
            except Exception as e:
                logger.warning(
                    "[Async Orchestrator] 子 Agent %s 第 %d 次执行失败: %s",
                    agent_name, attempt, e,
                )
                result.error = str(e)

        result.status = TaskStatus.FAILED
        self._results.append(result)
        return result

    # —— 结果汇总 ———————————————————————————————

    def _aggregate_results(self, task: str, sub_results: list[TaskResult]) -> TaskResult:
        """汇总子 Agent 结果（同步）。"""
        if self.master_agent.llm_client is not None:
            # LLM 汇总
            results_text = "\n\n".join(
                f"## {r.agent_name} 的结果\n{r.output}"
                for r in sub_results
                if r.is_success
            )
            failed_text = "\n".join(
                f"- {r.agent_name}: {r.error}"
                for r in sub_results
                if not r.is_success
            )

            summary_prompt = (
                f"用户原始任务：{task}\n\n"
                f"各子 Agent 的执行结果：\n{results_text}\n\n"
            )
            if failed_text:
                summary_prompt += f"失败的 Agent：\n{failed_text}\n\n"
            summary_prompt += "请根据以上结果，给用户一个完整、连贯的回答。"

            try:
                final_output = self.master_agent.run(summary_prompt)
            except Exception as e:
                final_output = f"汇总失败: {e}"

            return TaskResult(
                agent_name=self.master_agent.name,
                status=TaskStatus.COMPLETED,
                output=final_output,
                metadata={"sub_results": len(sub_results), "failed": sum(1 for r in sub_results if not r.is_success)},
            )
        else:
            # 规则模式：拼接结果
            success_outputs = [r.output for r in sub_results if r.is_success]
            combined = "\n\n---\n\n".join(success_outputs)
            return TaskResult(
                agent_name="orchestrator",
                status=TaskStatus.COMPLETED if success_outputs else TaskStatus.FAILED,
                output=combined,
                metadata={"sub_results": len(sub_results), "failed": sum(1 for r in sub_results if not r.is_success)},
            )

    async def _aaggregate_results(self, task: str, sub_results: list[TaskResult]) -> TaskResult:
        """汇总子 Agent 结果（异步）。"""
        if self.master_agent.llm_client is not None:
            results_text = "\n\n".join(
                f"## {r.agent_name} 的结果\n{r.output}"
                for r in sub_results
                if r.is_success
            )
            failed_text = "\n".join(
                f"- {r.agent_name}: {r.error}"
                for r in sub_results
                if not r.is_success
            )

            summary_prompt = (
                f"用户原始任务：{task}\n\n"
                f"各子 Agent 的执行结果：\n{results_text}\n\n"
            )
            if failed_text:
                summary_prompt += f"失败的 Agent：\n{failed_text}\n\n"
            summary_prompt += "请根据以上结果，给用户一个完整、连贯的回答。"

            try:
                final_output = await self.master_agent.arun(summary_prompt)
            except Exception as e:
                final_output = f"汇总失败: {e}"

            return TaskResult(
                agent_name=self.master_agent.name,
                status=TaskStatus.COMPLETED,
                output=final_output,
                metadata={"sub_results": len(sub_results), "failed": sum(1 for r in sub_results if not r.is_success)},
            )
        else:
            success_outputs = [r.output for r in sub_results if r.is_success]
            combined = "\n\n---\n\n".join(success_outputs)
            return TaskResult(
                agent_name="orchestrator",
                status=TaskStatus.COMPLETED if success_outputs else TaskStatus.FAILED,
                output=combined,
                metadata={"sub_results": len(sub_results), "failed": sum(1 for r in sub_results if not r.is_success)},
            )

    # —— 调度计划解析 ———————————————————————————————

    @staticmethod
    def _parse_dispatch(dispatch_text: str) -> list[tuple[str, str]]:
        """从主 Agent 的输出中解析调度计划。

        期望格式：
            AGENT: weather
            INPUT: 北京天气

            AGENT: writer
            INPUT: 根据天气写建议

        Returns:
            [(agent_name, task_input), ...] 列表
        """
        plan: list[tuple[str, str]] = []
        lines = dispatch_text.strip().split("\n")

        current_agent: str | None = None
        current_input: str = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.upper().startswith("AGENT:"):
                # 保存前一个
                if current_agent is not None:
                    plan.append((current_agent, current_input.strip()))

                current_agent = line.split(":", 1)[1].strip()
                current_input = ""

            elif line.upper().startswith("INPUT:"):
                current_input = line.split(":", 1)[1].strip()

            elif current_agent is not None:
                # 可能是续行
                current_input += " " + line

        # 最后一个
        if current_agent is not None:
            plan.append((current_agent, current_input.strip()))

        return plan

    @property
    def results(self) -> list[TaskResult]:
        """获取最近一次执行的子任务结果列表。"""
        return list(self._results)


# ── 流水线 Pipeline ──────────────────────────────────────────────


class Pipeline:
    """流水线模式 — 多个 Agent 顺序执行，前一个的输出是后一个的输入。

    适用场景：
        - 数据处理流水线（提取 → 转换 → 加载）
        - 多步推理（分析 → 规划 → 执行 → 验证）
        - 内容生成（研究 → 撰写 → 校对）

    使用示例::

        pipeline = Pipeline([
            Agent(name="researcher", system_prompt="你负责调研"),
            Agent(name="writer", system_prompt="你负责写作"),
            Agent(name="reviewer", system_prompt="你负责审校"),
        ])
        result = pipeline.run("写一篇关于 AI Agent 的文章")
    """

    def __init__(self, agents: list[Agent] | None = None) -> None:
        self._agents: list[Agent] = agents or []

    def add_stage(self, agent: Agent) -> None:
        """添加流水线阶段。"""
        self._agents.append(agent)

    def run(self, initial_input: str) -> TaskResult:
        """执行流水线（同步）。

        Args:
            initial_input: 初始输入

        Returns:
            最终阶段的 TaskResult
        """
        if not self._agents:
            return TaskResult(status=TaskStatus.FAILED, error="流水线为空")

        current_input = initial_input
        results: list[TaskResult] = []

        for i, agent in enumerate(self._agents):
            stage_name = f"stage_{i}_{agent.name}"
            logger.info("[Pipeline] 阶段 %d: %s", i, stage_name)

            try:
                output = agent.run(current_input)
                result = TaskResult(
                    agent_name=agent.name,
                    status=TaskStatus.COMPLETED,
                    output=output,
                    metadata={"stage": i},
                )
                current_input = output
            except Exception as e:
                logger.error("[Pipeline] 阶段 %d (%s) 失败: %s", i, agent.name, e)
                result = TaskResult(
                    agent_name=agent.name,
                    status=TaskStatus.FAILED,
                    error=str(e),
                    metadata={"stage": i},
                )
                # 流水线中断
                results.append(result)
                return TaskResult(
                    agent_name="pipeline",
                    status=TaskStatus.FAILED,
                    output="",
                    error=f"阶段 {i} ({agent.name}) 失败: {e}",
                    metadata={"stage_results": [r.__dict__ for r in results]},
                )

            results.append(result)
            logger.info("[Pipeline] 阶段 %d 完成", i)

        final = results[-1]
        final.metadata["total_stages"] = len(self._agents)
        return final

    async def arun(self, initial_input: str) -> TaskResult:
        """执行流水线（异步）。"""
        if not self._agents:
            return TaskResult(status=TaskStatus.FAILED, error="流水线为空")

        current_input = initial_input
        results: list[TaskResult] = []

        for i, agent in enumerate(self._agents):
            try:
                output = await agent.arun(current_input)
                result = TaskResult(
                    agent_name=agent.name,
                    status=TaskStatus.COMPLETED,
                    output=output,
                    metadata={"stage": i},
                )
                current_input = output
            except Exception as e:
                result = TaskResult(
                    agent_name=agent.name,
                    status=TaskStatus.FAILED,
                    error=str(e),
                    metadata={"stage": i},
                )
                results.append(result)
                return TaskResult(
                    agent_name="pipeline",
                    status=TaskStatus.FAILED,
                    output="",
                    error=f"阶段 {i} ({agent.name}) 失败: {e}",
                    metadata={"stage_results": [r.__dict__ for r in results]},
                )

            results.append(result)

        final = results[-1]
        final.metadata["total_stages"] = len(self._agents)
        return final


# ── 多模式协作团队 AgentTeam ──────────────────────────────────


class TeamMode(str, Enum):
    """团队协作模式。"""

    ORCHESTRATOR = "orchestrator"
    PIPELINE = "pipeline"
    ROUND_ROBIN = "round_robin"


class AgentTeam:
    """多模式协作团队 — 统一管理 Agent 集合，支持切换协作模式。

    使用示例::

        team = AgentTeam(
            name="analysis_team",
            mode=TeamMode.ORCHESTRATOR,
            master=coordinator_agent,
        )
        team.add_member(Agent(name="researcher", ...))
        team.add_member(Agent(name="writer", ...))

        result = team.run("分析市场趋势并写报告")
    """

    def __init__(
        self,
        name: str = "team",
        mode: TeamMode = TeamMode.ORCHESTRATOR,
        master: Agent | None = None,
    ) -> None:
        self.name = name
        self.mode = mode
        self.master = master or Agent(name="default_master")
        self._members: list[Agent] = []
        self._last_result: TaskResult | None = None

    def add_member(self, agent: Agent) -> None:
        """添加团队成员。"""
        self._members.append(agent)
        logger.info("[Team %s] 添加成员: %s", self.name, agent.name)

    @property
    def members(self) -> list[Agent]:
        return list(self._members)

    def run(self, task: str) -> TaskResult:
        """按当前模式执行团队任务（同步）。"""
        if self.mode == TeamMode.ORCHESTRATOR:
            return self._run_orchestrator(task)
        elif self.mode == TeamMode.PIPELINE:
            return self._run_pipeline(task)
        elif self.mode == TeamMode.ROUND_ROBIN:
            return self._run_round_robin(task)
        else:
            raise AgentError(f"不支持的团队模式: {self.mode}")

    async def arun(self, task: str) -> TaskResult:
        """按当前模式执行团队任务（异步）。"""
        if self.mode == TeamMode.ORCHESTRATOR:
            return await self._arun_orchestrator(task)
        elif self.mode == TeamMode.PIPELINE:
            return await self._arun_pipeline(task)
        elif self.mode == TeamMode.ROUND_ROBIN:
            return await self._arun_round_robin(task)
        else:
            raise AgentError(f"不支持的团队模式: {self.mode}")

    def _run_orchestrator(self, task: str) -> TaskResult:
        sub_agents = [
            SubAgent(name=a.name, agent=a, description=a.description or a.system_prompt[:100])
            for a in self._members
        ]
        orch = Orchestrator(master_agent=self.master, sub_agents=sub_agents)
        self._last_result = orch.run(task)
        return self._last_result

    async def _arun_orchestrator(self, task: str) -> TaskResult:
        sub_agents = [
            SubAgent(name=a.name, agent=a, description=a.description or a.system_prompt[:100])
            for a in self._members
        ]
        orch = Orchestrator(master_agent=self.master, sub_agents=sub_agents)
        self._last_result = await orch.arun(task)
        return self._last_result

    def _run_pipeline(self, task: str) -> TaskResult:
        pipeline = Pipeline(agents=[self.master] + self._members)
        self._last_result = pipeline.run(task)
        return self._last_result

    async def _arun_pipeline(self, task: str) -> TaskResult:
        pipeline = Pipeline(agents=[self.master] + self._members)
        self._last_result = await pipeline.arun(task)
        return self._last_result

    def _run_round_robin(self, task: str) -> TaskResult:
        """轮询模式：每个成员依次处理同一任务，补充前人的结果。"""
        all_agents = [self.master] + self._members
        context = task
        results: list[TaskResult] = []

        for agent in all_agents:
            try:
                output = agent.run(context)
                results.append(TaskResult(
                    agent_name=agent.name,
                    status=TaskStatus.COMPLETED,
                    output=output,
                ))
                context = output  # 下一个 Agent 基于前人的输出继续
            except Exception as e:
                results.append(TaskResult(
                    agent_name=agent.name,
                    status=TaskStatus.FAILED,
                    error=str(e),
                ))

        # 最终结果
        final_output = context
        self._last_result = TaskResult(
            agent_name=self.name,
            status=TaskStatus.COMPLETED if any(r.is_success for r in results) else TaskStatus.FAILED,
            output=final_output,
            metadata={"rounds": len(results), "failed": sum(1 for r in results if not r.is_success)},
        )
        return self._last_result

    async def _arun_round_robin(self, task: str) -> TaskResult:
        all_agents = [self.master] + self._members
        context = task
        results: list[TaskResult] = []

        for agent in all_agents:
            try:
                output = await agent.arun(context)
                results.append(TaskResult(
                    agent_name=agent.name,
                    status=TaskStatus.COMPLETED,
                    output=output,
                ))
                context = output
            except Exception as e:
                results.append(TaskResult(
                    agent_name=agent.name,
                    status=TaskStatus.FAILED,
                    error=str(e),
                ))

        self._last_result = TaskResult(
            agent_name=self.name,
            status=TaskStatus.COMPLETED if any(r.is_success for r in results) else TaskStatus.FAILED,
            output=context,
            metadata={"rounds": len(results), "failed": sum(1 for r in results if not r.is_success)},
        )
        return self._last_result

    @property
    def last_result(self) -> TaskResult | None:
        """获取最近一次执行的结果。"""
        return self._last_result

    def __repr__(self) -> str:
        return (
            f"AgentTeam(name={self.name!r}, mode={self.mode.value}, "
            f"master={self.master.name!r}, members={len(self._members)})"
        )
