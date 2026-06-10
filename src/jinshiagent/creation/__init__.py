"""内容创作模块 — 短视频/自媒体专属创作工具集

为小红书、抖音、快手、B站、知乎、今日头条、微博、微信公众号等
主流自媒体平台提供专业的文案、脚本、标题、标签、封面模板。

核心组件:
    - templates: 平台专属创作模板（文案/脚本/标题/标签/封面）
    - generator: 一键/批量生成引擎
    - prompts: 系统 prompt 与创作指令库
"""

from jinshiagent.creation.templates import (
    PLATFORMS,
    PlatformConfig,
    ContentTemplate,
    TemplateType,
    get_platform_config,
    list_platforms,
)
from jinshiagent.creation.generator import (
    ContentGenerator,
    ContentBundle,
    TopicBundle,
    GenerationResult,
)
from jinshiagent.creation.prompts import (
    CREATION_SYSTEM_PROMPT,
    CREATION_COMMANDS,
    get_command_prompt,
)

__all__ = [
    "PLATFORMS",
    "PlatformConfig",
    "ContentTemplate",
    "TemplateType",
    "get_platform_config",
    "list_platforms",
    "ContentGenerator",
    "ContentBundle",
    "TopicBundle",
    "GenerationResult",
    "CREATION_SYSTEM_PROMPT",
    "CREATION_COMMANDS",
    "get_command_prompt",
]
