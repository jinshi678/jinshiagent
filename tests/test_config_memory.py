"""配置加载与记忆模块单元测试"""

import pytest

from jinshiagent.config.loader import load_config
from jinshiagent.memory.short_term import ShortTermMemory


class TestConfigLoader:
    """配置加载测试"""

    def test_load_without_file(self) -> None:
        """不存在的配置文件应返回环境变量配置"""
        config = load_config("nonexistent.yaml")
        assert isinstance(config, dict)

    def test_env_override(self) -> None:
        """环境变量应覆盖配置文件"""
        import os
        os.environ["LOG_LEVEL"] = "DEBUG"
        try:
            config = load_config("nonexistent.yaml")
            assert config.get("log_level") == "DEBUG"
        finally:
            del os.environ["LOG_LEVEL"]


class TestShortTermMemory:
    """短期记忆测试"""

    def test_add_and_get(self) -> None:
        memory = ShortTermMemory()
        memory.add("user", "你好")
        memory.add("assistant", "你好！")
        assert len(memory) == 2
        ctx = memory.get_context()
        assert ctx[0].role == "user"
        assert ctx[1].role == "assistant"

    def test_max_messages(self) -> None:
        memory = ShortTermMemory(max_messages=3)
        for i in range(5):
            memory.add("user", f"消息 {i}")
        assert len(memory) == 3
        assert memory.messages[0].content == "消息 2"

    def test_to_openai_messages(self) -> None:
        memory = ShortTermMemory()
        memory.add("system", "你是一个助手")
        memory.add("user", "你好")
        msgs = memory.to_openai_messages()
        assert msgs[0] == {"role": "system", "content": "你是一个助手"}
        assert msgs[1] == {"role": "user", "content": "你好"}

    def test_clear(self) -> None:
        memory = ShortTermMemory()
        memory.add("user", "测试")
        memory.clear()
        assert len(memory) == 0
