"""工具增强与多 Agent 协作单元测试

测试内容：
    - 工具增强装饰器（retry, timeout, validate）
    - 多 Agent 协作框架（Orchestrator, Pipeline, AgentTeam）
    - 工具参数校验和错误处理
"""

from __future__ import annotations

import sys
import os
import time
import asyncio
import tempfile
import shutil

# 添加 src 到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jinshiagent.core.agent import Agent
from jinshiagent.core.tool_registry import ToolRegistry
from jinshiagent.core.multi_agent import (
    AgentTeam,
    Orchestrator,
    Pipeline,
    SubAgent,
    TaskResult,
    TaskStatus,
    TeamMode,
)
from jinshiagent.tools.tool_enhancements import (
    retry,
    timeout,
    validate,
    ToolTimeoutError,
)


# ── 辅助函数 ──────────────────────────────────────────────


def run_test(name: str, func) -> None:
    """运行单个测试并打印结果。"""
    try:
        func()
        print(f"  [PASS] {name}")
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")


# ── 工具增强测试 ──────────────────────────────────────────


def test_retry_success():
    """测试 retry 装饰器正常工作。"""
    call_count = 0

    @retry(max_retries=3, delay=0.1)
    def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("模拟网络错误")
        return "success"

    result = flaky_func()
    assert result == "success", f"期望 'success', 得到 {result!r}"
    assert call_count == 2, f"期望调用 2 次, 实际 {call_count}"


def test_retry_exhausted():
    """测试 retry 装饰器重试耗尽后抛出异常。"""
    @retry(max_retries=2, delay=0.05, exceptions=(ValueError,))
    def always_fail():
        raise ValueError("总是失败")

    try:
        always_fail()
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "总是失败" in str(e)


def test_timeout_normal():
    """测试 timeout 装饰器正常执行。"""
    @timeout(seconds=5)
    def fast_func():
        return "fast"

    result = fast_func()
    assert result == "fast"


def test_timeout_exceeded():
    """测试 timeout 装饰器超时抛出异常。"""
    @timeout(seconds=0.5)
    def slow_func():
        time.sleep(2)
        return "slow"

    try:
        slow_func()
        assert False, "应该抛出 ToolTimeoutError"
    except ToolTimeoutError as e:
        assert "超时" in str(e)


def test_validate_correct_types():
    """测试 validate 装饰器类型正确时正常通过。"""
    @validate(name=str, age=int)
    def greet(name: str, age: int) -> str:
        return f"{name} is {age}"

    result = greet("Alice", 30)
    assert result == "Alice is 30"


def test_validate_auto_convert():
    """测试 validate 装饰器自动类型转换。"""
    @validate(count=int)
    def process(count: int) -> int:
        return count * 2

    result = process(count="5")  # 字符串自动转 int
    assert result == 10


def test_validate_wrong_type():
    """测试 validate 装饰器类型不匹配时抛出异常。"""
    @validate(count=int)
    def process(count: int) -> int:
        return count

    try:
        process(count="not_a_number")
        assert False, "应该抛出 TypeError"
    except TypeError as e:
        assert "count" in str(e)


def test_validate_missing_param():
    """测试 validate 装饰器缺少必要参数。"""
    @validate(city=str)
    def get_weather(city: str) -> str:
        return f"weather in {city}"

    try:
        get_weather()
        assert False, "应该抛出 TypeError"
    except TypeError:
        pass  # 预期


def test_calculator_tool():
    """测试计算器工具。"""
    from jinshiagent.tools.calculator_tool import calculator

    assert calculator("2 + 3") == "5"
    assert calculator("10 * 8 + 3") == "83"
    assert calculator("2 ** 10") == "1024"
    assert "除以零" in calculator("1 / 0")
    assert "语法错误" in calculator("invalid!!")


def test_tool_registry_with_enhancements():
    """测试带增强装饰器的工具在注册表中正常工作。"""
    registry = ToolRegistry()

    @registry.register
    @retry(max_retries=2, delay=0.05)
    @validate(x=int, y=int)
    def safe_divide(x: int, y: int) -> str:
        if y == 0:
            raise ValueError("除以零")
        return str(x / y)

    # 正常调用
    result = registry.call("safe_divide", x=10, y=2)
    assert result == "5.0"

    # 参数自动转换
    result = registry.call("safe_divide", x="6", y="3")
    assert result == "2.0"


# ── 多 Agent 协作测试 ────────────────────────────────────


class MockLLMClient:
    """模拟 LLM 客户端。"""

    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or ["mock response"]
        self._idx = 0

    def chat_with_tools(self, messages, tools=None, **kwargs):
        if self._idx < len(self.responses):
            resp = self.responses[self._idx]
            self._idx += 1
        else:
            resp = "default response"
        return {"role": "assistant", "content": resp}

    async def achat_with_tools(self, messages, tools=None, **kwargs):
        return self.chat_with_tools(messages, tools, **kwargs)


def test_orchestrator_rule_based():
    """测试 Orchestrator 规则模式（无 LLM）。"""
    agent_a = Agent(name="a", system_prompt="Agent A")
    agent_b = Agent(name="b", system_prompt="Agent B")

    orch = Orchestrator(
        master_agent=Agent(name="master"),
        sub_agents=[
            SubAgent(name="a", agent=agent_a, description="Agent A"),
            SubAgent(name="b", agent=agent_b, description="Agent B"),
        ],
    )

    result = orch.run("test task")
    # 规则模式下子 Agent 没有 LLM 会失败
    assert result.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)


def test_orchestrator_with_llm():
    """测试 Orchestrator LLM 模式。"""
    mock_llm = MockLLMClient(responses=[
        "AGENT: weather\nINPUT: Beijing\n\nAGENT: writer\nINPUT: Write advice",
        "Beijing: Sunny, 28C",
        "Good weather for outdoor activities",
        "Based on the results: Beijing is sunny, go outside!",
    ])
    master = Agent(name="coordinator", llm_client=mock_llm)
    weather = Agent(name="weather", llm_client=mock_llm)
    writer = Agent(name="writer", llm_client=mock_llm)

    orch = Orchestrator(
        master_agent=master,
        sub_agents=[
            SubAgent(name="weather", agent=weather, description="Query weather"),
            SubAgent(name="writer", agent=writer, description="Write advice"),
        ],
    )

    result = orch.run("Check Beijing weather and give advice")
    assert result.is_success


def test_orchestrator_dispatch_parsing():
    """测试调度计划解析。"""
    dispatch_text = (
        "AGENT: weather\n"
        "INPUT: Beijing weather\n\n"
        "AGENT: writer\n"
        "INPUT: Write travel advice based on weather"
    )

    plan = Orchestrator._parse_dispatch(dispatch_text)
    assert len(plan) == 2
    assert plan[0] == ("weather", "Beijing weather")
    assert plan[1] == ("writer", "Write travel advice based on weather")


def test_pipeline():
    """测试 Pipeline 流水线。"""
    mock_llm = MockLLMClient(responses=["Step 1 done", "Step 2 done", "Final step"])
    agent1 = Agent(name="step1", llm_client=mock_llm)
    agent2 = Agent(name="step2", llm_client=mock_llm)

    pipeline = Pipeline(agents=[agent1, agent2])
    result = pipeline.run("pipeline task")
    assert result.is_success
    assert result.output == "Step 2 done"  # 最后一个阶段的输出


def test_pipeline_failure():
    """测试 Pipeline 中间阶段失败。"""
    class FailLLM:
        def chat_with_tools(self, messages, tools=None, **kwargs):
            raise RuntimeError("LLM error")

    agent1 = Agent(name="step1", llm_client=MockLLMClient(responses=["ok"]))
    agent2 = Agent(name="step2", llm_client=FailLLM())

    pipeline = Pipeline(agents=[agent1, agent2])
    result = pipeline.run("test")
    assert result.status == TaskStatus.FAILED
    assert "step2" in result.error


def test_agent_team():
    """测试 AgentTeam 团队模式。"""
    mock_llm = MockLLMClient(responses=["team response"])
    master = Agent(name="coordinator", llm_client=mock_llm)
    member = Agent(name="worker", llm_client=mock_llm)

    team = AgentTeam(name="test_team", mode=TeamMode.ORCHESTRATOR, master=master)
    team.add_member(member)

    assert len(team.members) == 1
    result = team.run("test task")
    assert isinstance(result, TaskResult)


def test_sub_agent_not_found():
    """测试子 Agent 不存在时的错误处理。"""
    mock_llm = MockLLMClient()
    master = Agent(name="master", llm_client=mock_llm)

    orch = Orchestrator(master_agent=master)
    # 直接调用不存在的子 Agent
    result = orch._execute_sub_agent("nonexistent", "task")
    assert result.status == TaskStatus.FAILED
    assert "不存在" in result.error


def test_task_result():
    """测试 TaskResult 数据模型。"""
    r1 = TaskResult(agent_name="a", status=TaskStatus.COMPLETED, output="done")
    assert r1.is_success
    assert r1.status == TaskStatus.COMPLETED

    r2 = TaskResult(agent_name="b", status=TaskStatus.FAILED, error="fail")
    assert not r2.is_success


# ── 异步测试 ──────────────────────────────────────────────


def test_async_orchestrator():
    """测试异步 Orchestrator。"""
    async def _test():
        mock_llm = MockLLMClient(responses=[
            "AGENT: worker\nINPUT: async task",
            "async result",
            "final summary",
        ])
        master = Agent(name="coordinator", llm_client=mock_llm)
        worker = Agent(name="worker", llm_client=mock_llm)

        orch = Orchestrator(
            master_agent=master,
            sub_agents=[SubAgent(name="worker", agent=worker, description="Worker")],
        )

        result = await orch.arun("async task")
        assert isinstance(result, TaskResult)

    asyncio.run(_test())


def test_async_pipeline():
    """测试异步 Pipeline。"""
    async def _test():
        mock_llm = MockLLMClient(responses=["async step 1", "async step 2"])
        agent = Agent(name="step1", llm_client=mock_llm)

        pipeline = Pipeline(agents=[agent])
        result = await pipeline.arun("async pipeline")
        assert isinstance(result, TaskResult)

    asyncio.run(_test())


# ── 运行所有测试 ──────────────────────────────────────────


def main():
    print("=" * 60)
    print("  工具增强与多 Agent 协作单元测试")
    print("=" * 60)

    print("\n[工具增强测试]")
    run_test("retry 正常工作", test_retry_success)
    run_test("retry 重试耗尽", test_retry_exhausted)
    run_test("timeout 正常执行", test_timeout_normal)
    run_test("timeout 超时异常", test_timeout_exceeded)
    run_test("validate 类型正确", test_validate_correct_types)
    run_test("validate 自动类型转换", test_validate_auto_convert)
    run_test("validate 类型不匹配", test_validate_wrong_type)
    run_test("validate 缺少参数", test_validate_missing_param)
    run_test("calculator 工具", test_calculator_tool)
    run_test("工具增强 + 注册表", test_tool_registry_with_enhancements)

    print("\n[多 Agent 协作测试]")
    run_test("Orchestrator 规则模式", test_orchestrator_rule_based)
    run_test("Orchestrator LLM 模式", test_orchestrator_with_llm)
    run_test("Orchestrator 调度解析", test_orchestrator_dispatch_parsing)
    run_test("Pipeline 流水线", test_pipeline)
    run_test("Pipeline 中间失败", test_pipeline_failure)
    run_test("AgentTeam 团队", test_agent_team)
    run_test("子 Agent 不存在", test_sub_agent_not_found)
    run_test("TaskResult 数据模型", test_task_result)

    print("\n[异步测试]")
    run_test("异步 Orchestrator", test_async_orchestrator)
    run_test("异步 Pipeline", test_async_pipeline)

    print("\n" + "=" * 60)
    print("  所有测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
