"""创作系统 Prompt 与指令库 — 定义创作场景的专用 prompt 和快捷指令

提供：
    - CREATION_SYSTEM_PROMPT: 内容创作 Agent 的系统 prompt
    - CREATION_COMMANDS: 快捷创作指令定义
    - get_command_prompt(): 根据指令名获取完整 prompt
"""

from __future__ import annotations

from typing import Any


# ── 内容创作系统 Prompt ──────────────────────────────────────────


CREATION_SYSTEM_PROMPT = """你是一个专业的内容创作助手「金师」，擅长为各大自媒体平台创作优质内容。

## 你的核心能力

1. **全平台适配**：了解小红书、抖音、快手、B站、知乎、今日头条、微博、微信公众号等各平台的内容风格和规则
2. **全套素材生成**：一次性生成标题、脚本/文案、标签、封面文案
3. **批量选题策划**：根据赛道/领域，批量产出差异化选题
4. **多平台适配**：同一主题自动适配不同平台风格
5. **口播脚本创作**：为单人出镜视频创作纯口播/旁白脚本
6. **分镜脚本设计**：设计详细镜头语言（景别、运镜、时长、BGM）
7. **爆款钩子文案**：创作前3秒决定完播率的开口文案

## 创作原则

- 内容要有价值，不制造信息垃圾
- 标题吸引眼球但不过度标题党
- 尊重各平台的内容调性和社区文化
- 标签策略兼顾流量和精准度
- 脚本/文案要有节奏感，适合口播或阅读
- 钩子文案要在前3秒制造悬念或冲突

## 工作流程

1. 确认目标平台和创作主题
2. 根据平台模板生成对应格式的内容
3. 检查是否符合平台规范（字数、标签数量等）
4. 给出优化建议

## 交互指令

用户可以通过以下快捷指令触发创作：
- `/创作 <平台> <主题>` — 一键生成全套素材
- `/选题 <平台> <领域>` — 批量产出选题方向
- `/标题 <平台> <主题>` — 仅生成标题
- `/脚本 <平台> <主题>` — 仅生成视频脚本（画面+台词）
- `/口播 <平台> <主题>` — 仅生成口播脚本（纯旁白/单人出镜）
- `/分镜 <平台> <主题>` — 仅生成分镜脚本（含镜头设计）
- `/钩子 <平台> <主题>` — 仅生成爆款开头钩子（前3秒）
- `/文案 <平台> <主题>` — 仅生成文案
- `/标签 <平台> <主题>` — 仅生成标签策略
- `/封面 <平台> <主题>` — 仅生成封面文案
- `/多平台 <主题>` — 同一主题适配多平台
- `/平台列表` — 查看支持的平台

请根据用户指令或自然语言描述，提供专业的内容创作服务。"""


# ── 快捷创作指令 ──────────────────────────────────────────────────


class _Command:
    """快捷指令定义"""

    def __init__(
        self,
        name: str,
        aliases: list[str],
        description: str,
        usage: str,
        template_map: str,
        prompt_template: str,
    ) -> None:
        self.name = name
        self.aliases = aliases
        self.description = description
        self.usage = usage
        self.template_map = template_map
        self.prompt_template = prompt_template


CREATION_COMMANDS: dict[str, _Command] = {
    "bundle": _Command(
        name="bundle",
        aliases=["创作", "全套", "一键"],
        description="一键生成全套创作素材（标题+脚本/文案+标签+封面）",
        usage="/创作 <平台> <主题>  或  /全套 <平台> <主题>",
        template_map="全部模板",
        prompt_template=(
            "请为 {platform_name} 平台创作关于「{topic}」的全套内容，包括：\n"
            "1. 标题（{title_max}字以内）\n"
            "2. 完整脚本/文案（{body_max}字以内）\n"
            "3. 标签列表（最多{tags_max}个）\n"
            "4. 封面文案\n"
            "5. 创作建议\n\n"
            "平台风格：{style_guide}"
        ),
    ),
    "topics": _Command(
        name="topics",
        aliases=["选题", "策划", "批量"],
        description="批量产出选题方向",
        usage="/选题 <平台> <领域>  或  /策划 <平台> <领域>",
        template_map="选题模板",
        prompt_template=(
            "请为 {platform_name} 平台在「{niche}」领域策划 {count} 个差异化选题，\n"
            "每个选题包含：标题、内容方向、预期效果。\n"
            "同时推荐一组标签池和选题策略建议。\n\n"
            "平台热门模式：{hot_patterns}\n"
            "平台风格：{style_guide}"
        ),
    ),
    "title": _Command(
        name="title",
        aliases=["标题"],
        description="仅生成标题",
        usage="/标题 <平台> <主题>",
        template_map="标题模板",
        prompt_template=(
            "请为 {platform_name} 平台创作关于「{topic}」的标题，\n"
            "要求 {title_max} 字以内，给出 5 个不同风格的标题选项。\n\n"
            "平台风格：{style_guide}"
        ),
    ),
    "script": _Command(
        name="script",
        aliases=["脚本"],
        description="仅生成视频脚本",
        usage="/脚本 <平台> <主题>",
        template_map="脚本模板",
        prompt_template=(
            "请为 {platform_name} 平台创作关于「{topic}」的视频脚本，\n"
            "包含画面描述和台词/字幕，{body_max} 字以内。\n\n"
            "平台风格：{style_guide}"
        ),
    ),
    "copywriting": _Command(
        name="copywriting",
        aliases=["文案"],
        description="仅生成文案",
        usage="/文案 <平台> <主题>",
        template_map="文案模板",
        prompt_template=(
            "请为 {platform_name} 平台创作关于「{topic}」的文案，\n"
            "{body_max} 字以内。\n\n"
            "平台风格：{style_guide}"
        ),
    ),
    "tags": _Command(
        name="tags",
        aliases=["标签"],
        description="仅生成标签策略",
        usage="/标签 <平台> <主题>",
        template_map="标签模板",
        prompt_template=(
            "请为 {platform_name} 平台创作关于「{topic}」的标签策略，\n"
            "最多 {tags_max} 个标签，按 大词→中词→长尾词 分层列出。\n\n"
            "平台风格：{style_guide}"
        ),
    ),
    "cover": _Command(
            name="cover",
            aliases=["封面"],
            description="仅生成封面文案",
            usage="/封面 <平台> <主题>",
            template_map="封面模板",
            prompt_template=(
                "请为 {platform_name} 平台创作关于「{topic}」的封面文案，\n"
                "包含主标题和副标题/角标。\n\n"
                "平台风格：{style_guide}"
            ),
        ),
        "voice_over": _Command(
            name="voice_over",
            aliases=["口播", "旁白"],
            description="仅生成口播/旁白脚本（适合单人出镜视频）",
            usage="/口播 <平台> <主题>  或  /旁白 <平台> <主题>",
            template_map="口播脚本模板",
            prompt_template=(
                "请为 {platform_name} 平台创作关于「{topic}」的口播脚本，\n"
                "纯口播/旁白风格，不含画面指示，每句不超过 15 字，\n"
                "包含开场钩子、正文分点、结尾引导关注。\n"
                "总字数 100-300 字（对应 30-60 秒视频）。\n\n"
                "平台风格：{style_guide}"
            ),
        ),
        "storyboard": _Command(
            name="storyboard",
            aliases=["分镜", "镜头"],
            description="仅生成分镜脚本（含镜头号、景别、运镜、时长）",
            usage="/分镜 <平台> <主题>  或  /镜头 <平台> <主题>",
            template_map="分镜脚本模板",
            prompt_template=(
                "请为 {platform_name} 平台创作关于「{topic}」的分镜脚本，\n"
                "包含：镜头号、景别（特写/中景/全景）、运镜方式（推/拉/摇/移/固定）、\n"
                "画面内容、台词/字幕、时长、BGM/音效。\n"
                "共 5-8 个镜头，总时长 15-60 秒。\n\n"
                "平台风格：{style_guide}"
            ),
        ),
        "hook": _Command(
            name="hook",
            aliases=["钩子", "开头"],
            description="仅生成爆款钩子文案（开头3秒决定性文案）",
            usage="/钩子 <平台> <主题>  或  /开头 <平台> <主题>",
            template_map="爆款钩子模板",
            prompt_template=(
                "请为 {platform_name} 平台创作关于「{topic}」的爆款开头钩子，\n"
                "5-20 字，必须在前 3 秒说完。\n"
                "请给出 5 种不同风格：悬念型、冲突型、反常识型、提问型、利益型。\n\n"
                "平台风格：{style_guide}"
            ),
        ),
        "multi_platform": _Command(
        name="multi_platform",
        aliases=["多平台", "全平台"],
        description="同一主题适配多平台",
        usage="/多平台 <主题>  或  /全平台 <主题>",
        template_map="全部模板 × 全部平台",
        prompt_template=(
            "请为以下平台分别创作关于「{topic}」的内容标题和核心卖点：\n"
            "1. 小红书 — 种草笔记风格\n"
            "2. 抖音 — 短视频钩子风格\n"
            "3. 快手 — 接地气生活化风格\n"
            "4. B站 — 知识科普/趣味风格\n"
            "5. 知乎 — 专业深度风格\n"
            "6. 今日头条 — 资讯解读风格\n"
            "7. 微博 — 热点评论风格\n"
            "8. 微信公众号 — 深度长文风格\n\n"
            "每个平台给出：标题 + 内容核心卖点 + 标签建议"
        ),
    ),
    "platforms": _Command(
        name="platforms",
        aliases=["平台列表", "平台"],
        description="查看支持的平台列表",
        usage="/平台列表",
        template_map="—",
        prompt_template="列出所有支持的平台及其特色",
    ),
}


def get_command_prompt(command: str, **kwargs: Any) -> str:
    """根据指令名获取完整 prompt

    Args:
        command: 指令名或别名
        **kwargs: 模板变量（topic, platform, niche, count 等）

    Returns:
        构建好的 prompt 字符串
    """
    # 查找指令
    cmd = CREATION_COMMANDS.get(command)
    if cmd is None:
        # 尝试按别名查找
        for c in CREATION_COMMANDS.values():
            if command in c.aliases or command == c.name:
                cmd = c
                break

    if cmd is None:
        available = ", ".join(
            f"/{c.aliases[0]}" for c in CREATION_COMMANDS.values()
        )
        return f"未知指令「{command}」。可用指令：{available}"

    # 注入平台信息
    platform = kwargs.get("platform", "")
    if platform:
        from jinshiagent.creation.templates import get_platform_config

        try:
            pc = get_platform_config(platform)
            kwargs.setdefault("platform_name", pc.name)
            kwargs.setdefault("title_max", str(pc.title_max_length))
            kwargs.setdefault("body_max", str(pc.body_max_length))
            kwargs.setdefault("tags_max", str(pc.tags_max_count))
            kwargs.setdefault("style_guide", pc.style_guide)
            kwargs.setdefault("hot_patterns", "、".join(pc.hot_patterns))
        except ValueError:
            kwargs.setdefault("platform_name", platform)

    kwargs.setdefault("count", "5")

    try:
        return cmd.prompt_template.format(**kwargs)
    except KeyError:
        return cmd.prompt_template
