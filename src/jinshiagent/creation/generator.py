"""内容生成引擎 — 一键/批量生成短视频创作素材

核心功能:
    - 一键生成全套素材（标题+脚本/文案+标签+封面）
    - 批量产出选题（按平台+主题自动生成多个选题方向）
    - 单项生成（仅标题/仅脚本/仅标签等）
    - 多平台适配（同一内容自动适配不同平台风格）

使用示例::

    from jinshiagent.creation import ContentGenerator, get_platform_config

    gen = ContentGenerator()
    result = gen.generate_bundle(
        topic="AI 绘画入门",
        platform="douyin",
    )
    print(result.title)
    print(result.script)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from jinshiagent.creation.templates import (
    PLATFORMS,
    ContentTemplate,
    PlatformConfig,
    TemplateType,
    get_platform_config,
)

logger = logging.getLogger("jinshiagent.creation.generator")


# ── 输出数据模型 ──────────────────────────────────────────────────


class ContentBundle(BaseModel):
    """一键生成的全套内容素材"""

    topic: str = Field(..., description="创作主题")
    platform: str = Field(..., description="目标平台 ID")
    platform_name: str = Field("", description="目标平台名称")
    title: str = Field("", description="标题")
    script: str = Field("", description="脚本/文案内容")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    cover: str = Field("", description="封面文案")
    tips: list[str] = Field(default_factory=list, description="创作建议")
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class TopicBundle(BaseModel):
    """批量选题结果"""

    niche: str = Field(..., description="创作领域/赛道")
    platform: str = Field(..., description="目标平台 ID")
    topics: list[dict[str, str]] = Field(default_factory=list, description="选题列表")
    tags_pool: list[str] = Field(default_factory=list, description="推荐标签池")
    tips: list[str] = Field(default_factory=list, description="选题策略建议")


class GenerationResult(BaseModel):
    """生成结果（支持成功/失败状态）"""

    success: bool = Field(True, description="是否生成成功")
    data: ContentBundle | TopicBundle | None = Field(None, description="生成内容")
    error: str = Field("", description="错误信息")
    platform: str = Field("", description="目标平台")


# ── Prompt 构建器 ──────────────────────────────────────────────────


class PromptBuilder:
    """根据平台模板构建 LLM prompt"""

    @staticmethod
    def build_bundle_prompt(
        topic: str,
        platform_config: PlatformConfig,
        extra_requirements: str = "",
    ) -> str:
        """构建一键生成全套素材的 prompt"""
        # 收集所有模板的结构说明
        templates_info = []
        for t in platform_config.templates:
            templates_info.append(
                f"### {t.name}（{t.template_type.value}）\n"
                f"结构：{t.structure}\n"
                f"示例：{t.example}"
            )

        prompt = (
            f"你是一个专业的内容创作助手，现在需要为 **{platform_config.name}** 平台 "
            f"创作关于「**{topic}**」的内容。\n\n"
            f"## 平台风格指南\n{platform_config.style_guide}\n\n"
            f"## 平台规范\n"
            f"- 标题最长 {platform_config.title_max_length} 字\n"
            f"- 正文最长 {platform_config.body_max_length} 字\n"
            f"- 标签最多 {platform_config.tags_max_count} 个\n\n"
            f"## 参考模板\n" + "\n\n".join(templates_info) + "\n\n"
        )

        if extra_requirements:
            prompt += f"## 额外要求\n{extra_requirements}\n\n"

        prompt += (
            "## 输出格式\n"
            "请严格按照以下 JSON 格式输出，不要添加任何其他文字：\n"
            "```json\n"
            "{\n"
            '  "title": "标题内容",\n'
            '  "script": "脚本/文案完整内容",\n'
            '  "tags": ["标签1", "标签2", "标签3"],\n'
            '  "cover": "封面文案",\n'
            '  "tips": ["创作建议1", "创作建议2"]\n'
            "}\n"
            "```"
        )
        return prompt

    @staticmethod
    def build_topic_prompt(
        niche: str,
        platform_config: PlatformConfig,
        count: int = 5,
    ) -> str:
        """构建批量选题 prompt"""
        hot_patterns = "、".join(platform_config.hot_patterns)
        prompt = (
            f"你是一个专业的内容策划师，现在需要为 **{platform_config.name}** 平台 "
            f"在「**{niche}**」领域策划 {count} 个选题。\n\n"
            f"## 平台热门内容模式\n{hot_patterns}\n\n"
            f"## 平台风格\n{platform_config.style_guide}\n\n"
            f"## 要求\n"
            f"- 每个选题需要包含：标题、内容方向、预期效果\n"
            f"- 选题要覆盖不同热门模式\n"
            f"- 选题要有差异化，不要重复\n\n"
            f"## 输出格式\n"
            "请严格按照以下 JSON 格式输出，不要添加任何其他文字：\n"
            "```json\n"
            "{\n"
            f'  "topics": [\n'
            "    {\n"
            '      "title": "选题标题",\n'
            '      "direction": "内容方向简述",\n'
            '      "expected_effect": "预期效果"\n'
            "    }\n"
            "  ],\n"
            '  "tags_pool": ["推荐标签1", "推荐标签2", "推荐标签3"],\n'
            '  "tips": ["选题策略建议1", "选题策略建议2"]\n'
            "}\n"
            "```"
        )
        return prompt

    @staticmethod
    def build_single_prompt(
        topic: str,
        platform_config: PlatformConfig,
        template_type: TemplateType,
        extra_requirements: str = "",
    ) -> str:
        """构建单项生成的 prompt（仅标题/仅脚本/仅标签等）"""
        templates = platform_config.get_templates(template_type)
        template_info = ""
        if templates:
            t = templates[0]
            template_info = (
                f"## 参考模板：{t.name}\n"
                f"结构：{t.structure}\n"
                f"示例：{t.example}\n"
                f"技巧：{'、'.join(t.tips)}\n"
            )

        type_names = {
            TemplateType.TITLE: "标题",
            TemplateType.SCRIPT: "脚本/文案",
            TemplateType.VOICE_OVER: "口播脚本",
            TemplateType.STORYBOARD: "分镜脚本",
            TemplateType.COPYWRITING: "文案",
            TemplateType.TAGS: "标签",
            TemplateType.COVER: "封面文案",
            TemplateType.HOOK: "爆款钩子文案",
            TemplateType.TOPIC: "选题",
        }
        type_name = type_names.get(template_type, template_type.value)

        prompt = (
            f"你是一个专业的内容创作助手，现在需要为 **{platform_config.name}** 平台 "
            f"创作关于「**{topic}**」的**{type_name}**。\n\n"
            f"## 平台风格指南\n{platform_config.style_guide}\n"
        )

        if template_type == TemplateType.TITLE:
            prompt += f"\n标题最长 {platform_config.title_max_length} 字\n"
        elif template_type in (TemplateType.SCRIPT, TemplateType.COPYWRITING):
            prompt += f"\n正文最长 {platform_config.body_max_length} 字\n"
        elif template_type == TemplateType.VOICE_OVER:
            prompt += f"\n口播脚本建议 100-300 字（对应 30-60 秒视频），每句不超过 15 字\n"
        elif template_type == TemplateType.STORYBOARD:
            prompt += f"\n分镜建议 5-8 个镜头，总时长 15-60 秒，每个镜头标注景别和运镜方式\n"
        elif template_type == TemplateType.HOOK:
            prompt += f"\n钩子文案 5-20 字，必须在前 3 秒说完，制造悬念或冲突\n"
        elif template_type == TemplateType.TAGS:
            prompt += f"\n标签最多 {platform_config.tags_max_count} 个\n"

        if template_info:
            prompt += f"\n{template_info}\n"

        if extra_requirements:
            prompt += f"## 额外要求\n{extra_requirements}\n\n"

        prompt += f"请直接输出{type_name}内容，不需要额外解释。"
        return prompt


# ── 内容生成引擎 ──────────────────────────────────────────────────


class ContentGenerator:
    """内容生成引擎 — 支持一键/批量/单项生成

    可以配合 Agent 使用（通过 LLM 生成），也可以直接返回 prompt
    供外部 LLM 调用。

    使用示例::

        gen = ContentGenerator()

        # 一键生成全套素材
        result = gen.generate_bundle(
            topic="AI 绘画入门",
            platform="douyin",
        )

        # 批量选题
        topics = gen.generate_topics(
            niche="AI 工具",
            platform="xiaohongshu",
            count=5,
        )

        # 仅生成标题
        title = gen.generate_single(
            topic="ChatGPT 使用技巧",
            platform="bilibili",
            template_type=TemplateType.TITLE,
        )
    """

    def __init__(self, llm_client: Any = None) -> None:
        """初始化生成引擎

        Args:
            llm_client: LLM 客户端实例（可选）
                如果提供，generate_* 方法会调用 LLM 生成内容
                如果不提供，generate_* 方法返回构建好的 prompt
        """
        self.llm_client = llm_client
        self._prompt_builder = PromptBuilder()

    def generate_bundle(
        self,
        topic: str,
        platform: str,
        extra_requirements: str = "",
    ) -> ContentBundle:
        """一键生成全套创作素材

        Args:
            topic: 创作主题
            platform: 目标平台 ID
            extra_requirements: 额外要求

        Returns:
            ContentBundle 全套素材
        """
        platform_config = get_platform_config(platform)
        prompt = self._prompt_builder.build_bundle_prompt(
            topic=topic,
            platform_config=platform_config,
            extra_requirements=extra_requirements,
        )

        if self.llm_client is None:
            # 无 LLM，返回 prompt 供外部使用
            return ContentBundle(
                topic=topic,
                platform=platform,
                platform_name=platform_config.name,
                title=f"[需要 LLM 生成] Prompt 已构建",
                script=prompt,
                tags=[],
                cover="",
                tips=platform_config.style_guide.split("，")[:3],
                metadata={"prompt": prompt, "mode": "prompt_only"},
            )

        # 调用 LLM 生成
        try:
            response = self._call_llm(prompt)
            return self._parse_bundle_response(response, topic, platform_config)
        except Exception as e:
            logger.error("生成失败: %s", e)
            return ContentBundle(
                topic=topic,
                platform=platform,
                platform_name=platform_config.name,
                title="",
                script="",
                tags=[],
                cover="",
                tips=[],
                metadata={"error": str(e)},
            )

    def generate_topics(
        self,
        niche: str,
        platform: str,
        count: int = 5,
    ) -> TopicBundle:
        """批量产出选题

        Args:
            niche: 创作领域/赛道
            platform: 目标平台 ID
            count: 选题数量

        Returns:
            TopicBundle 选题列表
        """
        platform_config = get_platform_config(platform)
        prompt = self._prompt_builder.build_topic_prompt(
            niche=niche,
            platform_config=platform_config,
            count=count,
        )

        if self.llm_client is None:
            return TopicBundle(
                niche=niche,
                platform=platform,
                topics=[{"title": "[需要 LLM 生成]", "direction": prompt, "expected_effect": ""}],
                tags_pool=[],
                tips=[],
            )

        try:
            response = self._call_llm(prompt)
            return self._parse_topic_response(response, niche, platform_config)
        except Exception as e:
            logger.error("选题生成失败: %s", e)
            return TopicBundle(
                niche=niche,
                platform=platform,
                topics=[],
                tags_pool=[],
                tips=[f"生成失败: {e}"],
            )

    def generate_single(
        self,
        topic: str,
        platform: str,
        template_type: TemplateType,
        extra_requirements: str = "",
    ) -> str:
        """单项生成（仅标题/仅脚本/仅标签等）

        Args:
            topic: 创作主题
            platform: 目标平台 ID
            template_type: 要生成的类型
            extra_requirements: 额外要求

        Returns:
            生成的内容文本
        """
        platform_config = get_platform_config(platform)
        prompt = self._prompt_builder.build_single_prompt(
            topic=topic,
            platform_config=platform_config,
            template_type=template_type,
            extra_requirements=extra_requirements,
        )

        if self.llm_client is None:
            return prompt

        try:
            return self._call_llm(prompt)
        except Exception as e:
            logger.error("单项生成失败: %s", e)
            return f"生成失败: {e}"

    def generate_multi_platform(
        self,
        topic: str,
        platforms: list[str] | None = None,
        extra_requirements: str = "",
    ) -> list[ContentBundle]:
        """同一主题适配多平台

        Args:
            topic: 创作主题
            platforms: 目标平台列表（默认全部平台）
            extra_requirements: 额外要求

        Returns:
            每个平台的 ContentBundle 列表
        """
        if platforms is None:
            platforms = list(PLATFORMS.keys())

        results = []
        for pid in platforms:
            try:
                bundle = self.generate_bundle(
                    topic=topic,
                    platform=pid,
                    extra_requirements=extra_requirements,
                )
                results.append(bundle)
            except Exception as e:
                logger.warning("平台 %s 生成失败: %s", pid, e)
                results.append(ContentBundle(
                    topic=topic,
                    platform=pid,
                    platform_name=PLATFORMS[pid].name,
                    metadata={"error": str(e)},
                ))

        return results

    # ── 内部方法 ──────────────────────────────────────────────

    def _call_llm(self, prompt: str) -> str:
        """调用 LLM 生成内容"""
        if self.llm_client is None:
            raise RuntimeError("llm_client 未配置")

        messages = [{"role": "user", "content": prompt}]

        # 适配不同 LLM 客户端接口
        if hasattr(self.llm_client, "chat"):
            result = self.llm_client.chat(messages=messages)
            if isinstance(result, dict):
                return result.get("content", str(result))
            return str(result)
        elif hasattr(self.llm_client, "chat_with_tools"):
            result = self.llm_client.chat_with_tools(messages=messages, tools=None)
            if isinstance(result, dict):
                return result.get("content", str(result))
            return str(result)
        else:
            raise RuntimeError(
                f"不支持的 LLM 客户端类型: {type(self.llm_client)}"
            )

    def _parse_bundle_response(
        self,
        response: str,
        topic: str,
        platform_config: PlatformConfig,
    ) -> ContentBundle:
        """解析 LLM 返回的全套素材 JSON"""
        # 尝试提取 JSON
        json_str = self._extract_json(response)
        if json_str:
            try:
                data = json.loads(json_str)
                return ContentBundle(
                    topic=topic,
                    platform=platform_config.id,
                    platform_name=platform_config.name,
                    title=data.get("title", ""),
                    script=data.get("script", ""),
                    tags=data.get("tags", []),
                    cover=data.get("cover", ""),
                    tips=data.get("tips", []),
                )
            except json.JSONDecodeError:
                pass

        # JSON 解析失败，将整个响应作为 script
        return ContentBundle(
            topic=topic,
            platform=platform_config.id,
            platform_name=platform_config.name,
            script=response,
            tips=["LLM 未返回标准 JSON 格式，请检查输出"],
        )

    def _parse_topic_response(
        self,
        response: str,
        niche: str,
        platform_config: PlatformConfig,
    ) -> TopicBundle:
        """解析 LLM 返回的选题 JSON"""
        json_str = self._extract_json(response)
        if json_str:
            try:
                data = json.loads(json_str)
                return TopicBundle(
                    niche=niche,
                    platform=platform_config.id,
                    topics=data.get("topics", []),
                    tags_pool=data.get("tags_pool", []),
                    tips=data.get("tips", []),
                )
            except json.JSONDecodeError:
                pass

        return TopicBundle(
            niche=niche,
            platform=platform_config.id,
            topics=[{"title": response, "direction": "", "expected_effect": ""}],
            tips=["LLM 未返回标准 JSON 格式"],
        )

    @staticmethod
    def _extract_json(text: str) -> str | None:
        """从文本中提取 JSON 块"""
        # 优先提取 ```json ... ``` 代码块
        import re
        match = re.search(r"```json\s*\n(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 尝试提取花括号包裹的 JSON
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)

        return None
