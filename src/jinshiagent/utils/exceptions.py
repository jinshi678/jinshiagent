"""异常体系 — JinshiAgent 统一异常层级

所有 JinshiAgent 异常均继承自 JinshiAgentError，便于统一捕获与处理。

层级::

    JinshiAgentError
    ├── ConfigError         配置加载/解析错误
    ├── LLMError           LLM 调用失败
    ├── ToolError          工具执行错误
    ├── MemoryError        记忆存储/检索错误
    └── WorkflowError      工作流编排/执行错误

使用示例::

    from jinshiagent.utils.exceptions import JinshiAgentError, LLMError

    try:
        client.chat("hello")
    except LLMError as e:
        print(f"LLM 调用失败: {e}")
    except JinshiAgentError as e:
        print(f"框架错误: {e}")
"""


class JinshiAgentError(Exception):
    """JinshiAgent 基础异常"""

    def __init__(self, message: str = "", *, details: str = "") -> None:
        self.details = details
        full = f"{message} — {details}" if details else message
        super().__init__(full)


class ConfigError(JinshiAgentError):
    """配置加载/解析错误"""


class LLMError(JinshiAgentError):
    """LLM 调用失败"""


class ToolError(JinshiAgentError):
    """工具执行错误"""


class MemoryError(JinshiAgentError):
    """记忆存储/检索错误"""


class WorkflowError(JinshiAgentError):
    """工作流编排/执行错误"""
