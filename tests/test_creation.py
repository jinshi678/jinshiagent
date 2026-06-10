"""内容创作模块单元测试"""

import pytest

from jinshiagent.creation.templates import (
    PLATFORMS,
    ContentTemplate,
    PlatformConfig,
    TemplateType,
    get_platform_config,
    list_platforms,
)
from jinshiagent.creation.generator import (
    ContentBundle,
    ContentGenerator,
    TopicBundle,
    PromptBuilder,
)
from jinshiagent.creation.prompts import (
    CREATION_SYSTEM_PROMPT,
    CREATION_COMMANDS,
    get_command_prompt,
)


class TestTemplates:
    """创作模板测试"""

    def test_all_platforms_exist(self):
        """8 大平台都应存在。"""
        expected = {"xiaohongshu", "douyin", "kuaishou", "bilibili",
                    "zhihu", "toutiao", "weibo", "wechat"}
        assert set(PLATFORMS.keys()) == expected

    def test_platform_config_structure(self):
        """每个平台配置应有完整的属性。"""
        for pid, config in PLATFORMS.items():
            assert isinstance(config, PlatformConfig)
            assert config.id == pid
            assert config.name  # 中文名非空
            assert config.icon  # emoji 非空
            assert config.title_max_length > 0
            assert config.body_max_length > 0
            assert config.tags_max_count > 0
            assert config.style_guide  # 风格指南非空
            assert len(config.templates) > 0  # 至少有1个模板

    def test_get_platform_config_valid(self):
        """有效平台应返回配置。"""
        config = get_platform_config("douyin")
        assert config.name == "抖音"

    def test_get_platform_config_invalid(self):
        """无效平台应抛出 ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            get_platform_config("invalid_platform")

    def test_list_platforms(self):
        """list_platforms 应返回所有平台信息。"""
        platforms = list_platforms()
        assert len(platforms) == 8
        assert all("id" in p and "name" in p and "icon" in p for p in platforms)

    def test_get_templates_by_type(self):
        """按类型筛选模板。"""
        xhs = get_platform_config("xiaohongshu")
        titles = xhs.get_templates(TemplateType.TITLE)
        assert len(titles) > 0
        assert all(t.template_type == TemplateType.TITLE for t in titles)

    def test_template_has_required_fields(self):
        """每个模板应有完整的字段。"""
        for pid, config in PLATFORMS.items():
            for t in config.templates:
                assert t.name
                assert t.template_type in TemplateType
                assert t.platform == pid
                assert t.structure
                assert t.example

    def test_xiaohongshu_templates(self):
        """小红书应有种草笔记、探店攻略、标题、标签、封面、选题模板。"""
        xhs = get_platform_config("xiaohongshu")
        types = {t.template_type for t in xhs.templates}
        assert TemplateType.COPYWRITING in types
        assert TemplateType.TITLE in types
        assert TemplateType.TAGS in types
        assert TemplateType.COVER in types
        assert TemplateType.TOPIC in types

    def test_douyin_has_script_template(self):
        """抖音应有视频脚本模板。"""
        dy = get_platform_config("douyin")
        types = {t.template_type for t in dy.templates}
        assert TemplateType.SCRIPT in types

    def test_bilibili_has_script_template(self):
        """B站应有知识区视频脚本模板。"""
        bili = get_platform_config("bilibili")
        scripts = bili.get_templates(TemplateType.SCRIPT)
        assert len(scripts) > 0
        assert "UP主" in scripts[0].example or "三连" in scripts[0].example


class TestGenerator:
    """内容生成引擎测试"""

    def test_generator_no_llm_bundle(self):
        """无 LLM 时 generate_bundle 应返回 prompt。"""
        gen = ContentGenerator()
        result = gen.generate_bundle(topic="AI绘画", platform="douyin")
        assert isinstance(result, ContentBundle)
        assert result.topic == "AI绘画"
        assert result.platform == "douyin"
        assert result.platform_name == "抖音"
        assert "prompt" in result.metadata or len(result.script) > 0

    def test_generator_no_llm_topics(self):
        """无 LLM 时 generate_topics 应返回结果。"""
        gen = ContentGenerator()
        result = gen.generate_topics(niche="AI工具", platform="xiaohongshu")
        assert isinstance(result, TopicBundle)
        assert result.niche == "AI工具"
        assert result.platform == "xiaohongshu"

    def test_generator_no_llm_single(self):
        """无 LLM 时 generate_single 应返回 prompt 文本。"""
        gen = ContentGenerator()
        result = gen.generate_single(
            topic="ChatGPT技巧",
            platform="bilibili",
            template_type=TemplateType.TITLE,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generator_invalid_platform(self):
        """无效平台应抛出 ValueError。"""
        gen = ContentGenerator()
        with pytest.raises(ValueError, match="不存在"):
            gen.generate_bundle(topic="测试", platform="invalid")

    def test_generate_multi_platform(self):
        """多平台生成应返回每个平台的结果。"""
        gen = ContentGenerator()
        results = gen.generate_multi_platform(
            topic="AI绘画",
            platforms=["douyin", "xiaohongshu"],
        )
        assert len(results) == 2
        assert results[0].platform != results[1].platform

    def test_generate_multi_platform_default_all(self):
        """不指定平台时默认全部8个。"""
        gen = ContentGenerator()
        results = gen.generate_multi_platform(topic="AI绘画")
        assert len(results) == 8


class TestPromptBuilder:
    """Prompt 构建器测试"""

    def test_build_bundle_prompt(self):
        """一键生成 prompt 应包含平台信息。"""
        from jinshiagent.creation.templates import get_platform_config
        pc = get_platform_config("douyin")
        prompt = PromptBuilder.build_bundle_prompt(
            topic="AI绘画入门", platform_config=pc,
        )
        assert "抖音" in prompt
        assert "AI绘画入门" in prompt
        assert "JSON" in prompt

    def test_build_topic_prompt(self):
        """选题 prompt 应包含领域信息。"""
        from jinshiagent.creation.templates import get_platform_config
        pc = get_platform_config("xiaohongshu")
        prompt = PromptBuilder.build_topic_prompt(
            niche="美妆", platform_config=pc, count=5,
        )
        assert "小红书" in prompt
        assert "美妆" in prompt
        assert "5" in prompt

    def test_build_single_prompt(self):
        """单项 prompt 应包含模板类型。"""
        from jinshiagent.creation.templates import get_platform_config
        pc = get_platform_config("bilibili")
        prompt = PromptBuilder.build_single_prompt(
            topic="Python教程", platform_config=pc,
            template_type=TemplateType.TITLE,
        )
        assert "B站" in prompt
        assert "标题" in prompt


class TestPrompts:
    """创作指令与 prompt 测试"""

    def test_creation_system_prompt_exists(self):
        """系统 prompt 应存在且包含创作相关内容。"""
        assert CREATION_SYSTEM_PROMPT
        assert "创作" in CREATION_SYSTEM_PROMPT
        assert "金师" in CREATION_SYSTEM_PROMPT

    def test_commands_completeness(self):
        """所有指令应有完整定义。"""
        expected = {"bundle", "topics", "title", "script", "copywriting",
                    "tags", "cover", "multi_platform", "platforms"}
        assert set(CREATION_COMMANDS.keys()) == expected

    def test_command_aliases(self):
        """每个指令应有中文别名。"""
        for cmd in CREATION_COMMANDS.values():
            assert len(cmd.aliases) > 0
            assert cmd.prompt_template

    def test_get_command_prompt_bundle(self):
        """获取 bundle 指令 prompt。"""
        prompt = get_command_prompt(
            "bundle",
            platform="douyin",
            topic="AI绘画",
        )
        assert "抖音" in prompt

    def test_get_command_prompt_by_alias(self):
        """通过别名获取指令 prompt。"""
        prompt = get_command_prompt("创作", platform="douyin", topic="测试")
        assert "抖音" in prompt

    def test_get_command_prompt_unknown(self):
        """未知指令应返回提示。"""
        prompt = get_command_prompt("不存在的指令")
        assert "未知指令" in prompt

    def test_get_command_prompt_topics(self):
        """选题 prompt。"""
        prompt = get_command_prompt(
            "topics",
            platform="xiaohongshu",
            niche="美妆",
            count="5",
        )
        assert "小红书" in prompt
        assert "美妆" in prompt


class TestGeneratorJsonParsing:
    """JSON 解析测试"""

    def test_extract_json_code_block(self):
        """提取 ```json ... ``` 格式的 JSON。"""
        text = '```json\n{"title": "测试", "script": "内容"}\n```'
        result = ContentGenerator._extract_json(text)
        assert result is not None
        assert "title" in result

    def test_extract_json_bare(self):
        """提取裸 JSON 对象。"""
        text = '这是一些文字 {"title": "测试"} 其他文字'
        result = ContentGenerator._extract_json(text)
        assert result is not None
        assert "title" in result

    def test_extract_json_none(self):
        """无 JSON 时返回 None。"""
        text = "这段文字没有 JSON"
        result = ContentGenerator._extract_json(text)
        assert result is None
