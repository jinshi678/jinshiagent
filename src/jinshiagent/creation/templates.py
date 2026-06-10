"""平台专属创作模板 — 覆盖 8 大主流自媒体平台

每个平台定义了完整的创作规范：标题格式、文案风格、脚本结构、标签策略、封面文案。
模板引擎根据平台特性自动适配内容格式与风格。

支持平台:
    - 小红书 (xiaohongshu): 种草笔记、生活分享、探店攻略
    - 抖音 (douyin): 短视频脚本、热点追踪、知识科普
    - 快手 (kuaishou): 接地气内容、生活记录、才艺展示
    - B站 (bilibili): 中长视频、知识区、游戏/生活区
    - 知乎 (zhihu): 深度图文、专业回答、专栏文章
    - 今日头条 (toutiao): 资讯图文、热点追踪、兴趣推荐
    - 微博 (weibo): 热搜话题、短图文、事件评论
    - 微信公众号 (wechat): 深度长文、品牌推文、行业分析
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── 枚举与数据模型 ──────────────────────────────────────────────────


class TemplateType(str, Enum):
    """模板类型枚举"""

    TITLE = "title"            # 标题模板
    SCRIPT = "script"          # 脚本模板（画面+台词）
    VOICE_OVER = "voice_over"  # 口播脚本（纯口播/旁白）
    STORYBOARD = "storyboard"   # 分镜脚本（详细镜头设计）
    COPYWRITING = "copywriting"  # 文案模板
    TAGS = "tags"              # 标签模板
    COVER = "cover"            # 封面文案模板
    HOOK = "hook"              # 爆款钩子模板（开头3秒）
    TOPIC = "topic"            # 选题模板


class ContentTemplate(BaseModel):
    """单个创作模板"""

    name: str = Field(..., description="模板名称")
    template_type: TemplateType = Field(..., description="模板类型")
    platform: str = Field(..., description="所属平台 ID")
    description: str = Field("", description="模板用途说明")
    structure: str = Field(..., description="模板结构/格式说明")
    example: str = Field(..., description="示例输出")
    tips: list[str] = Field(default_factory=list, description="创作技巧")
    variables: list[str] = Field(default_factory=list, description="模板中可替换的变量")


class PlatformConfig(BaseModel):
    """平台配置 — 定义一个自媒体平台的完整创作规范"""

    id: str = Field(..., description="平台唯一标识")
    name: str = Field(..., description="平台中文名")
    icon: str = Field("", description="平台标识 emoji")
    description: str = Field("", description="平台定位简介")
    content_types: list[str] = Field(default_factory=list, description="适合的内容类型")
    title_max_length: int = Field(30, description="标题最大字数")
    body_max_length: int = Field(2000, description="正文最大字数")
    tags_max_count: int = Field(10, description="标签最大数量")
    style_guide: str = Field("", description="整体风格指南")
    hot_patterns: list[str] = Field(default_factory=list, description="热门内容模式")
    templates: list[ContentTemplate] = Field(default_factory=list, description="专属模板列表")

    def get_templates(self, template_type: TemplateType | None = None) -> list[ContentTemplate]:
        """获取模板列表，可按类型筛选"""
        if template_type is None:
            return self.templates
        return [t for t in self.templates if t.template_type == template_type]


# ── 8 大平台配置 ──────────────────────────────────────────────────


XIAOHONGSHU = PlatformConfig(
    id="xiaohongshu",
    name="小红书",
    icon="📕",
    description="种草社区，生活方式分享平台",
    content_types=["种草笔记", "生活分享", "探店攻略", "美妆教程", "穿搭分享", "家居好物", "美食推荐"],
    title_max_length=20,
    body_max_length=1000,
    tags_max_count=15,
    style_guide=(
        "小红书风格：口语化、亲切感、使用emoji、分段清晰、"
        "多用感叹号和问号、强调「真实体验」和「干货分享」。"
        "标题要抓眼球、善用数字和对比。"
    ),
    hot_patterns=["对比测评", "好物清单", "教程攻略", "生活vlog", "穿搭日记"],
    templates=[
        ContentTemplate(
            name="种草笔记",
            template_type=TemplateType.COPYWRITING,
            platform="xiaohongshu",
            description="产品/体验种草推荐",
            structure=(
                "① 开头：引入痛点或场景（1-2句）\n"
                "② 正文：产品/体验介绍（3-5个要点，每点2-3句）\n"
                "③ 结尾：总结推荐+互动引导"
            ),
            example=(
                "姐妹们！！这个{产品名}真的绝了😭\n\n"
                "之前一直被{痛点}困扰，试了好多都不行...\n"
                "直到入手了这款！\n\n"
                "✨ 亮点1：{特点1}，真的超{形容词}\n"
                "✨ 亮点2：{特点2}，{使用感受}\n"
                "✨ 亮点3：{特点3}，性价比绝绝子\n\n"
                "💰 价格：{价格}，比同类便宜一半！\n"
                "📌 购买渠道：{购买渠道}\n\n"
                "真的不是广告！自用推荐！💕\n"
                "有问题评论区问我～"
            ),
            tips=[
                "开头用感叹词制造情绪共鸣",
                "多用emoji增加可读性",
                "要点式列举，每点一个卖点",
                "结尾加互动引导提升评论量",
                "价格和渠道信息增加可信度",
            ],
            variables=["产品名", "痛点", "特点1", "特点2", "特点3", "形容词", "使用感受", "价格", "购买渠道"],
        ),
        ContentTemplate(
            name="探店攻略",
            template_type=TemplateType.COPYWRITING,
            platform="xiaohongshu",
            description="线下探店/旅行攻略",
            structure=(
                "① 引入：目的地/店铺+亮点预告\n"
                "② 环境/交通：位置+氛围描述\n"
                "③ 体验过程：按时间线/分区描述\n"
                "④ 推荐+避坑：实用建议\n"
                "⑤ 总结：评分+适合人群"
            ),
            example=(
                "📍{店名} | 人均{价格}的{特色}，值不值？\n\n"
                "🔍 位置：{地址}，地铁{线路}站步行{时间}\n\n"
                "环境绝了！{环境描述}\n\n"
                "🍽️ 必点推荐：\n"
                "1️⃣ {菜品1} - {评价1}\n"
                "2️⃣ {菜品2} - {评价2}\n"
                "3️⃣ {菜品3} - {评价3}\n\n"
                "⚠️ 避坑：{避坑建议}\n\n"
                "⭐ 综合评分：{评分}/5\n"
                "适合：{适合人群}\n\n"
                "#探店 #{城市}美食 #{特色标签}"
            ),
            tips=["位置交通信息一定要写", "必点和避坑分开列出", "评分增加专业感", "标签要覆盖城市+品类"],
            variables=["店名", "价格", "特色", "地址", "线路", "时间", "环境描述", "菜品1-3", "评价1-3", "避坑建议", "评分", "适合人群", "城市", "特色标签"],
        ),
        ContentTemplate(
            name="标题模板",
            template_type=TemplateType.TITLE,
            platform="xiaohongshu",
            description="小红书爆款标题公式",
            structure="情绪词+数字+关键词+悬念/对比",
            example=(
                "① {形容词}！{数字}个{品类}闭眼入不踩雷\n"
                "② 被{数字}个人问爆的{品类}，终于出了！\n"
                "③ {品类}天花板？用完{时间}说真话\n"
                "④ {对比词}！{品类}到底选哪个？帮你{结果}\n"
                "⑤ 姐妹们冲！{价格}搞定{品类}，{效果}"
            ),
            tips=["20字以内", "善用数字", "制造悬念或对比", "加入情绪词"],
            variables=["形容词", "数字", "品类", "时间", "对比词", "结果", "价格", "效果"],
        ),
        ContentTemplate(
            name="标签策略",
            template_type=TemplateType.TAGS,
            platform="xiaohongshu",
            description="小红书标签布局策略",
            structure="大词+中词+长尾词，5-10个标签",
            example=(
                "#大品类 #{细分品类} #{品牌/产品名} "
                "#{场景} #{效果} #{人群} "
                "#{城市} #{价格带} #{风格}"
            ),
            tips=["前3个标签决定流量池", "大词引流+长尾词精准", "带上城市标签获取同城流量", "标签数5-10个最优"],
            variables=["大品类", "细分品类", "品牌/产品名", "场景", "效果", "人群", "城市", "价格带", "风格"],
        ),
        ContentTemplate(
            name="封面文案",
            template_type=TemplateType.COVER,
            platform="xiaohongshu",
            description="笔记封面配文模板",
            structure="大字标题+副标题/标签",
            example=(
                "主标题：{核心卖点}必看！\n"
                "副标题：{数字}个{品类}｜{价格}起\n"
                "角标：{限定词}"
            ),
            tips=["封面文字不超过8字", "大字+数字最吸引眼球", "角标增加紧迫感"],
            variables=["核心卖点", "数字", "品类", "价格", "限定词"],
        ),
        ContentTemplate(
            name="选题灵感",
            template_type=TemplateType.TOPIC,
            platform="xiaohongshu",
            description="小红书热门选题方向",
            structure="品类×场景×人群交叉组合",
            example=(
                "① {品类}入门指南｜新手必看{数字}条\n"
                "② {场景}必备{品类}清单\n"
                "③ {人群}的{品类}选择攻略\n"
                "④ {季节}限定{品类}推荐\n"
                "⑤ {品类}红黑榜｜{数字}款实测"
            ),
            tips=["结合季节和节日", "新手向内容流量大", "红黑榜对比容易爆", "清单体容易收藏"],
            variables=["品类", "场景", "人群", "数字", "季节"],
        ),
        ContentTemplate(
            name="口播脚本（视频笔记）",
            template_type=TemplateType.VOICE_OVER,
            platform="xiaohongshu",
            description="小红书视频笔记口播脚本（亲测分享风）",
            structure=(
                "① 打招呼+引入（亲切口播，1-2句）\n"
                "② 核心内容分点口播（3-5个要点）\n"
                "③ 真心话/避坑提示\n"
                "④ 引导互动（评论/收藏/关注）"
            ),
            example=(
                "【视频笔记口播：{主题}】\n\n"
                "哈喽宝宝们～今天来分享{主题}，{引入理由}！\n\n"
                "✨ 第一点：{要点1}\n"
                "（对应画面：{画面提示1}）\n\n"
                "✨ 第二点：{要点2}\n"
                "（对应画面：{画面提示2}）\n\n"
                "✨ 第三点：{要点3}\n"
                "（对应画面：{画面提示3}）\n\n"
                "💡 真心话：{避坑/真心建议}\n\n"
                "有问题评论区聊～记得收藏防止找不到！"
            ),
            tips=[
                "开头用「哈喽宝宝们」等亲昵称呼",
                "每点配合画面提示，方便后期剪辑",
                "加「真心话」板块增加真实感",
                "结尾引导评论+收藏+关注三连",
            ],
            variables=["主题", "引入理由", "要点1-3", "画面提示1-3", "避坑/真心建议"],
        ),
        ContentTemplate(
            name="分镜脚本（视频笔记）",
            template_type=TemplateType.STORYBOARD,
            platform="xiaohongshu",
            description="小红书视频笔记分镜（含镜头设计+字幕+贴纸提示）",
            structure="镜头号 | 时长 | 画面 | 口播 | 字幕/贴纸 | BGM",
            example=(
                "【分镜：{主题}】总时长：{总时长}秒\n\n"
                "| 镜头 | 时长 | 画面 | 口播 | 字幕/贴纸 | BGM |\n"
                "|------|------|------|------|------------|-----|\n"
                "| 1 | 2s | {开场画面} | {开场口播} | {开头字幕} | 轻快入场 |\n"
                "| 2 | 4s | {要点1画面} | {口播1} | {要点1字幕} | 同上 |\n"
                "| 3 | 4s | {要点2画面} | {口播2} | {要点2字幕}+🌟贴纸 | 同上 |\n"
                "| 4 | 4s | {要点3画面} | {口播3} | {要点3字幕} | 同上 |\n"
                "| 5 | 3s | {结尾画面} | {结尾口播} | {结尾字幕}+手指贴纸 | 渐弱 |\n\n"
                "📌 剪辑注意：{剪辑提示}\n"
                "📌 滤镜建议：{滤镜风格}"
            ),
            tips=[
                "每个镜头时长2-5秒，节奏轻快",
                "字幕用可爱字体，关键处加热贴纸",
                "结尾加手指指向下方的贴纸引导关注",
                "滤镜风格要统一，建议用VSCO或小红书自带滤镜",
            ],
            variables=["主题", "总时长", "开场画面/口播/字幕", "要点1-3画面/口播/字幕", "结尾画面/口播/字幕", "剪辑提示", "滤镜风格"],
        ),
        ContentTemplate(
            name="爆款开头钩子",
            template_type=TemplateType.HOOK,
            platform="xiaohongshu",
            description="小红书笔记开头第一句（决定点开率和读完率）",
            structure="情绪词+痛点/好奇+解决方案预告",
            example=(
                "【小红书爆款开头公式】\n\n"
                "① 情绪惊叹型：「天哪！{发现}...」\n"
                "② 痛点共鸣型：「有没有{痛点}的姐妹？」\n"
                "③ 反差对比型：「之前{误区}，现在{正确做法}」\n"
                "④ 干货预告型：「{数字}个{品类}干货，{效果}」\n"
                "⑤ 闺蜜分享型：「姐妹们！！{发现}」\n\n"
                "【适用于「{主题}」的开头选项】\n"
                "开头1：{开头文案1}\n"
                "开头2：{开头文案2}\n"
                "开头3：{开头文案3}"
            ),
            tips=[
                "第一句就要有情绪，用「！」「？」增强语气",
                "「姐妹们」是小红书最高频开头词",
                "痛点开头最容易引发共鸣和评论",
                "开头不超过20字，一眼要能看完",
            ],
            variables=["发现", "痛点", "误区", "正确做法", "数字", "品类", "效果", "主题", "开头文案1-3"],
        ),
    ],
)


DOUYIN = PlatformConfig(
    id="douyin",
    name="抖音",
    icon="🎵",
    description="短视频平台，强娱乐属性",
    content_types=["短视频脚本", "知识科普", "剧情演绎", "热点追踪", "好物推荐", "技能教学"],
    title_max_length=30,
    body_max_length=500,
    tags_max_count=8,
    style_guide=(
        "抖音风格：开头3秒定生死、节奏快、反转多、"
        "口语化短句、制造悬念、引导评论和关注。"
        "视频脚本要写出画面和台词。"
    ),
    hot_patterns=["反转剧情", "知识科普", "好物推荐", "教程教学", "热点评论"],
    templates=[
        ContentTemplate(
            name="短视频脚本",
            template_type=TemplateType.SCRIPT,
            platform="douyin",
            description="15-60秒短视频完整脚本",
            structure=(
                "① 钩子（0-3秒）：制造悬念/冲突\n"
                "② 展开（3-20秒）：核心内容/剧情推进\n"
                "③ 高潮（20-40秒）：反转/揭秘/干货\n"
                "④ 收尾（40-60秒）：总结+引导互动"
            ),
            example=(
                "【脚本：{主题}】时长：{时长}秒\n\n"
                "🎬 0-3秒 钩子：\n"
                "画面：{画面描述}\n"
                "台词/字幕：{钩子台词}\n\n"
                "🎬 3-20秒 展开：\n"
                "画面：{展开画面}\n"
                "台词/字幕：{展开内容}\n\n"
                "🎬 20-40秒 高潮：\n"
                "画面：{高潮画面}\n"
                "台词/字幕：{高潮内容}\n\n"
                "🎬 40-60秒 收尾：\n"
                "画面：{收尾画面}\n"
                "台词/字幕：{收尾台词}\n\n"
                "📌 BGM推荐：{音乐风格}\n"
                "📌 字幕样式：{字幕建议}"
            ),
            tips=[
                "前3秒决定用户是否停留",
                "每个片段不超过10秒",
                "台词要短，一句一换画面",
                "高潮部分必须有反转或惊喜",
                "结尾引导评论提升互动率",
            ],
            variables=["主题", "时长", "画面描述", "钩子台词", "展开画面", "展开内容", "高潮画面", "高潮内容", "收尾画面", "收尾台词", "音乐风格", "字幕建议"],
        ),
        ContentTemplate(
            name="知识科普脚本",
            template_type=TemplateType.SCRIPT,
            platform="douyin",
            description="1分钟知识科普视频脚本",
            structure="反常识开场→解释原理→举例说明→实用建议→引导关注",
            example=(
                "【科普脚本：{知识点}】\n\n"
                "⚡ 0-5秒：你不知道的是，{反常识陈述}！\n\n"
                "📖 5-25秒：其实这是因为{原理}。\n"
                "简单来说就是{通俗解释}。\n\n"
                "💡 25-45秒：举个例子，{具体例子}。\n"
                "所以{结论}。\n\n"
                "✅ 45-60秒：记住这{数字}点就够了：\n"
                "1. {要点1}\n"
                "2. {要点2}\n"
                "3. {要点3}\n\n"
                "关注我，每天学一点{领域}知识！"
            ),
            tips=["反常识开头最吸引人", "原理用比喻解释", "举生活中常见的例子", "结尾列出要点方便截图"],
            variables=["知识点", "反常识陈述", "原理", "通俗解释", "具体例子", "结论", "数字", "要点1-3", "领域"],
        ),
        ContentTemplate(
            name="标题模板",
            template_type=TemplateType.TITLE,
            platform="douyin",
            description="抖音爆款标题公式",
            structure="悬念/冲突+核心关键词+行动号召",
            example=(
                "① {悬念词}！{主题}的{结果}竟然是{意外}？\n"
                "② {数字}秒教会你{技能}，{效果}太绝了\n"
                "③ {人群}注意！{主题}的{数字}个真相\n"
                "④ 被{数字}万人收藏的{主题}，终于公开了\n"
                "⑤ {主题}到底怎么做？{结果}惊呆了"
            ),
            tips=["前10字最重要", "数字增加具体感", "制造信息差", "避免标题党过头"],
            variables=["悬念词", "主题", "结果", "意外", "数字", "技能", "效果", "人群"],
        ),
        ContentTemplate(
            name="标签策略",
            template_type=TemplateType.TAGS,
            platform="douyin",
            description="抖音话题标签布局",
            structure="热门话题+垂直话题+长尾话题",
            example=(
                "#{热门话题} #{垂直领域} #{细分话题} "
                "#{内容形式} #{场景} #{人群}"
            ),
            tips=["参与热门话题蹭流量", "垂直话题提升精准度", "话题不超过5个", "原创话题提升辨识度"],
            variables=["热门话题", "垂直领域", "细分话题", "内容形式", "场景", "人群"],
        ),
        ContentTemplate(
            name="封面文案",
            template_type=TemplateType.COVER,
            platform="douyin",
            description="视频封面/缩略图文案",
            structure="大字标题+关键词高亮",
            example=(
                "主标题：{核心词}必看！\n"
                "副标题：{结果}/{数字}秒{动作}\n"
                "边框色：{颜色建议}"
            ),
            tips=["封面文字3-5字最优", "高亮关键词", "颜色对比要强", "人像+文字组合最吸引"],
            variables=["核心词", "结果", "数字", "动作", "颜色建议"],
        ),
        ContentTemplate(
            name="口播脚本",
            template_type=TemplateType.VOICE_OVER,
            platform="douyin",
            description="纯口播/旁白短视频脚本（无画面指示，适合单人出镜）",
            structure=(
                "① 钩子（0-3秒）：一句话制造悬念/冲突\n"
                "② 展开（3-30秒）：核心内容口播正文\n"
                "③ 结尾（30-60秒）：总结+引导关注\n"
                "附：BGM建议、字幕重点提示"
            ),
            example=(
                "【口播脚本：{主题}】时长：{时长}秒｜风格：{风格}\n\n"
                "🎙️ 开场钩子（0-3秒）：\n"
                "{钩子台词}（语速稍快，眼神直视镜头）\n\n"
                "🎙️ 正文展开（3-30秒）：\n"
                "{要点1内容}（停顿1秒）\n"
                "{要点2内容}（加重语气）\n"
                "{要点3内容}\n\n"
                "🎙️ 结尾收束（30-60秒）：\n"
                "{总结台词}\n"
                "记得点赞关注，下次见～\n\n"
                "📌 BGM建议：{音乐风格}（节奏：{节奏描述}）\n"
                "📌 字幕重点：{字幕关键词}（用黄字高亮）"
            ),
            tips=[
                "钩子台词要一句话制造好奇",
                "正文每句不超过15字，方便口播",
                "用括号标注语气/停顿/表情提示",
                "结尾固定引导关注话术",
                "BGM节奏要与内容情绪匹配",
            ],
            variables=["主题", "时长", "风格", "钩子台词", "要点1-3内容", "总结台词", "音乐风格", "节奏描述", "字幕关键词"],
        ),
        ContentTemplate(
            name="分镜脚本",
            template_type=TemplateType.STORYBOARD,
            platform="douyin",
            description="详细分镜脚本（含镜头号、景别、运镜、台词、时长）",
            structure=(
                "镜头号 | 景别 | 运镜方式 | 画面内容 | 台词/字幕 | 时长 | BGM/音效\n"
                "一般 5-8 个镜头，总时长 15-60 秒"
            ),
            example=(
                "【分镜脚本：{主题}】总时长：{总时长}秒\n\n"
                "| 镜头 | 景别 | 运镜 | 画面内容 | 台词/字幕 | 时长 | BGM/音效 |\n"
                "|------|------|------|----------|-----------|------|----------|\n"
                "| 1 | 特写 | 固定 | {画面1} | {字幕1} | 3s | {音效1} |\n"
                "| 2 | 中景 | 推镜头 | {画面2} | {台词2} | 5s | {BGM段落} |\n"
                "| 3 | 近景 | 摇镜头 | {画面3} | {字幕3} | 4s | 同上 |\n"
                "| 4 | 全景 | 拉镜头 | {画面4} | {字幕4} | 6s | {音乐高潮} |\n"
                "| 5 | 特写 | 固定 | {画面5} | {结尾字幕} | 3s | {结尾音效} |\n\n"
                "📌 拍摄要点：{拍摄注意事项}\n"
                "📌 道具准备：{道具清单}"
            ),
            tips=[
                "镜头不超过8个，便于拍摄",
                "景别要有变化（特写→中景→全景）",
                "每个镜头时长明确标注",
                "运镜方式要具体（推/拉/摇/移/固定）",
                "BGM标注具体入点和情绪",
            ],
            variables=["主题", "总时长", "画面1-5", "字幕1-4/结尾字幕", "台词2", "音效1/结尾音效", "BGM段落/音乐高潮", "拍摄注意事项", "道具清单"],
        ),
        ContentTemplate(
            name="爆款钩子文案",
            template_type=TemplateType.HOOK,
            platform="douyin",
            description="前3秒爆款钩子文案（决定完播率的关键）",
            structure="悬念型/冲突型/反常识型/提问型/利益型 — 5种钩子公式",
            example=(
                "【钩子类型库】\n\n"
                "① 悬念型：「你绝对不知道{事实}...」\n"
                "② 冲突型：「{常识}？大错特错！」\n"
                "③ 反常识型：「{常见做法}，其实完全错了」\n"
                "④ 提问型：「{人群}注意！{问题}你中了几条？」\n"
                "⑤ 利益型：「{数字}秒学会{技能}，{效果}」\n\n"
                "【适用于「{主题}」的钩子选项】\n"
                "钩子1（悬念型）：{钩子文案1}\n"
                "钩子2（冲突型）：{钩子文案2}\n"
                "钩子3（反常识型）：{钩子文案3}"
            ),
            tips=[
                "钩子不超过15字，要口语化",
                "必须制造「信息缺口」让人想看下去",
                "避免标题党，钩子内容要与视频主体相关",
                "测试钩子：读一遍，如果自己不想看下去就重写",
            ],
            variables=["事实", "常识", "常见做法", "人群", "问题", "数字", "技能", "效果", "主题", "钩子文案1-3"],
        ),
    ],
)


KUAISHOU = PlatformConfig(
    id="kuaishou",
    name="快手",
    icon="🎬",
    description="短视频社区，接地气、真实感",
    content_types=["生活记录", "才艺展示", "美食制作", "乡村日常", "搞笑段子", "直播带货"],
    title_max_length=30,
    body_max_length=500,
    tags_max_count=8,
    style_guide=(
        "快手风格：接地气、真实不做作、方言感、"
        "生活化场景、强调「老铁」和「家人」的亲近感。"
        "内容偏向实用和娱乐并重。"
    ),
    hot_patterns=["生活日常", "美食制作", "才艺展示", "乡村生活", "正能量"],
    templates=[
        ContentTemplate(
            name="生活记录脚本",
            template_type=TemplateType.SCRIPT,
            platform="kuaishou",
            description="日常生活记录类视频脚本",
            structure="自然开场→日常片段→情感升华→互动引导",
            example=(
                "【脚本：{主题}】\n\n"
                "🏠 开场：{日常场景描述}\n"
                "老铁们，今天给大家看看{内容}～\n\n"
                "📹 中间：{过程描述}\n"
                "{关键台词}\n\n"
                "❤️ 升华：{感悟/情感}\n"
                "生活就是这样，{金句}。\n\n"
                "💬 互动：你们{互动问题}？\n"
                "评论区聊聊！"
            ),
            tips=["开场要自然不做作", "过程要有细节", "情感升华不要太刻意", "互动问题要接地气"],
            variables=["主题", "日常场景描述", "内容", "过程描述", "关键台词", "感悟/情感", "金句", "互动问题"],
        ),
        ContentTemplate(
            name="标题模板",
            template_type=TemplateType.TITLE,
            platform="kuaishou",
            description="快手风格标题公式",
            structure="生活化表达+情感+行动号召",
            example=(
                "① 老铁们看看{内容}，{评价}！\n"
                "② {人物}的{日常}，太{形容词}了\n"
                "③ {内容}这样做，{结果}！\n"
                "④ 给{人物}点个赞，{原因}\n"
                "⑤ {场景}里的{内容}，看哭了"
            ),
            tips=["用「老铁」「家人」等称呼", "感情真挚不浮夸", "适当用方言增加亲切感"],
            variables=["内容", "评价", "人物", "日常", "形容词", "结果", "原因", "场景"],
        ),
        ContentTemplate(
            name="标签策略",
            template_type=TemplateType.TAGS,
            platform="kuaishou",
            description="快手话题标签布局",
            structure="地域+生活+情感话题",
            example=(
                "#{地域} #{生活场景} #{内容类型} "
                "#{情感词} #{人群标签}"
            ),
            tips=["地域标签获取同城流量", "生活类标签为主", "情感标签提升共鸣", "避免过度商业化标签"],
            variables=["地域", "生活场景", "内容类型", "情感词", "人群标签"],
        ),
    ],
)


BILIBILI = PlatformConfig(
    id="bilibili",
    name="B站",
    icon="📺",
    description="年轻人文化社区，知识+兴趣",
    content_types=["知识科普", "游戏实况", "影视解说", "技能教程", "生活vlog", "音乐舞蹈"],
    title_max_length=80,
    body_max_length=5000,
    tags_max_count=12,
    style_guide=(
        "B站风格：信息密度高、有梗、专业但不枯燥、"
        "弹幕友好、适当玩梗、节奏感强。"
        "标题可以稍长，但要有信息量。"
    ),
    hot_patterns=["硬核科普", "趣味教程", "影视解说", "评测对比", "生活vlog"],
    templates=[
        ContentTemplate(
            name="知识区视频脚本",
            template_type=TemplateType.SCRIPT,
            platform="bilibili",
            description="5-15分钟知识科普视频脚本",
            structure="开场引子→背景铺垫→核心内容→案例分析→总结升华→互动引导",
            example=(
                "【脚本：{主题}】预计时长：{时长}分钟\n\n"
                "🎬 开场（30秒）：\n"
                "大家好，我是{UP主名}。\n"
                "今天我们来聊一个{形容词}的话题——{主题}。\n"
                "先问大家一个问题：{问题}？\n\n"
                "📖 背景铺垫（1-2分钟）：\n"
                "{背景介绍}\n\n"
                "🔬 核心内容（3-8分钟）：\n"
                "一、{要点1标题}\n"
                "{要点1内容}\n\n"
                "二、{要点2标题}\n"
                "{要点2内容}\n\n"
                "三、{要点3标题}\n"
                "{要点3内容}\n\n"
                "💡 案例分析（1-2分钟）：\n"
                "{案例分析}\n\n"
                "🎯 总结（30秒）：\n"
                "所以总结一下：\n"
                "1. {总结1}\n"
                "2. {总结2}\n"
                "3. {总结3}\n\n"
                "如果觉得有帮助，别忘了三连支持！\n"
                "下期我们聊聊{下期预告}，别忘了关注～"
            ),
            tips=[
                "开场抛出问题制造好奇心",
                "核心内容分3-5个要点",
                "每个要点配合图示/动画",
                "适当玩梗但不能影响信息量",
                "弹幕互动点要提前埋好",
                "结尾三连+下期预告",
            ],
            variables=["主题", "时长", "UP主名", "形容词", "问题", "背景介绍", "要点1-3标题", "要点1-3内容", "案例分析", "总结1-3", "下期预告"],
        ),
        ContentTemplate(
            name="标题模板",
            template_type=TemplateType.TITLE,
            platform="bilibili",
            description="B站爆款标题公式",
            structure="信息量+趣味性+悬念",
            example=(
                "① 【{分区}】{主题}到底{疑问}？{数字}分钟讲透\n"
                "② {主题}的{数字}个真相，第{数字}个万万没想到\n"
                "③ 用{方法}搞定{问题}，{效果}！\n"
                "④ {主题}入门到精通｜{数字}分钟{效果}\n"
                "⑤ 关于{主题}，你需要知道的{数字}件事"
            ),
            tips=["可用分区前缀【】增加辨识度", "标题允许较长，但前20字最关键", "数字增加具体感", "适当加梗但不要影响搜索"],
            variables=["分区", "主题", "疑问", "数字", "方法", "问题", "效果"],
        ),
        ContentTemplate(
            name="标签策略",
            template_type=TemplateType.TAGS,
            platform="bilibili",
            description="B站标签/分区布局",
            structure="分区+主题标签+长尾标签",
            example=(
                "#{分区} #{主题} #{细分方向} "
                "#{内容形式} #{知识点1} #{知识点2}"
            ),
            tips=["分区标签必须准确", "前3个标签影响推荐", "加2-3个长尾标签", "标签要包含视频核心关键词"],
            variables=["分区", "主题", "细分方向", "内容形式", "知识点1", "知识点2"],
        ),
    ],
)


ZHIHU = PlatformConfig(
    id="zhihu",
    name="知乎",
    icon="💡",
    description="知识问答社区，深度内容平台",
    content_types=["专业回答", "专栏文章", "想法短文", "知识科普", "经验分享", "行业分析"],
    title_max_length=50,
    body_max_length=50000,
    tags_max_count=5,
    style_guide=(
        "知乎风格：专业严谨、逻辑清晰、有数据支撑、"
        "适当引用来源、用故事化叙事降低理解门槛。"
        "回答要有「干货感」和「独家视角」。"
    ),
    hot_patterns=["干货回答", "经验分享", "专业解读", "行业内幕", "对比分析"],
    templates=[
        ContentTemplate(
            name="专业回答",
            template_type=TemplateType.COPYWRITING,
            platform="zhihu",
            description="知乎高质量回答模板",
            structure="结论先行→分点论证→案例支撑→总结升华",
            example=(
                "**{核心结论}。**\n\n"
                "---\n\n"
                "这个问题我研究/经历过，直接说结论：{结论展开}。\n\n"
                "## 一、{要点1标题}\n\n"
                "{要点1论述}\n\n"
                "> {引用/数据支撑}\n\n"
                "## 二、{要点2标题}\n\n"
                "{要点2论述}\n\n"
                "举个例子：{案例}\n\n"
                "## 三、{要点3标题}\n\n"
                "{要点3论述}\n\n"
                "---\n\n"
                "### 总结\n\n"
                "{总结内容}\n\n"
                "以上，希望对你有帮助。如果觉得有用，点个赞让更多人看到～"
            ),
            tips=[
                "第一句话给出明确结论",
                "分点论证，每点一个核心论据",
                "用数据和引用增加可信度",
                "案例要具体且有代入感",
                "适当展示个人经历/专业背景",
            ],
            variables=["核心结论", "结论展开", "要点1-3标题", "要点1-3论述", "引用/数据支撑", "案例", "总结内容"],
        ),
        ContentTemplate(
            name="标题模板",
            template_type=TemplateType.TITLE,
            platform="zhihu",
            description="知乎文章/想法标题公式",
            structure="问题+角度/观点",
            example=(
                "① {主题}：{数字}个被忽视的真相\n"
                "② 为什么{现象}？{角度}解析\n"
                "③ {领域}从业者告诉你：{观点}\n"
                "④ {主题}的{数字}层认知，你在第几层？\n"
                "⑤ 从{角度}看{主题}，{结论}"
            ),
            tips=["标题体现专业度", "问题式标题搜索流量大", "加「从业者」「亲历」增加可信度", "避免标题党"],
            variables=["主题", "数字", "现象", "角度", "领域", "观点", "结论"],
        ),
    ],
)


TOUTIAO = PlatformConfig(
    id="toutiao",
    name="今日头条",
    icon="📰",
    description="资讯分发平台，兴趣推荐驱动",
    content_types=["热点资讯", "深度解读", "历史人文", "科技数码", "健康养生", "财经分析"],
    title_max_length=30,
    body_max_length=5000,
    tags_max_count=5,
    style_guide=(
        "今日头条风格：标题吸引眼球但不标题党、"
        "开头交代背景、正文信息量大、适当分段、"
        "数据引用增加可信度。"
    ),
    hot_patterns=["热点追踪", "深度解读", "数据盘点", "历史揭秘", "健康科普"],
    templates=[
        ContentTemplate(
            name="资讯图文",
            template_type=TemplateType.COPYWRITING,
            platform="toutiao",
            description="资讯类图文内容模板",
            structure="背景引入→事件经过→关键分析→各方观点→趋势预判",
            example=(
                "# {标题}\n\n"
                "{事件背景}，引发了{影响范围}关注。\n\n"
                "## 事件经过\n\n"
                "{经过描述}\n\n"
                "## 关键分析\n\n"
                "{分析内容}\n\n"
                "## 各方观点\n\n"
                "- {观点1来源}：{观点1内容}\n"
                "- {观点2来源}：{观点2内容}\n\n"
                "## 趋势预判\n\n"
                "{趋势分析}\n\n"
                "---\n"
                "*本文仅代表作者个人观点*"
            ),
            tips=["开头一段说清5W1H", "多用数据增加可信度", "各方观点保持中立", "标题不要过度夸张"],
            variables=["标题", "事件背景", "影响范围", "经过描述", "分析内容", "观点1-2来源", "观点1-2内容", "趋势分析"],
        ),
        ContentTemplate(
            name="标题模板",
            template_type=TemplateType.TITLE,
            platform="toutiao",
            description="头条爆款标题公式",
            structure="信息量+时效性+好奇心",
            example=(
                "① {事件}最新进展：{结果}\n"
                "② {数字}组数据看懂{主题}，{结论}\n"
                "③ {事件}背后：{角度}揭秘{真相}\n"
                "④ {权威来源}：{主题}{趋势}\n"
                "⑤ {主题}全解读：{数字}个关键变化"
            ),
            tips=["时效性是第一要素", "数字增加具体感", "加权威来源增加可信度", "避免纯标题党"],
            variables=["事件", "结果", "数字", "主题", "结论", "角度", "真相", "权威来源", "趋势"],
        ),
    ],
)


WEIBO = PlatformConfig(
    id="weibo",
    name="微博",
    icon="🔥",
    description="社交媒体平台，热点话题发源地",
    content_types=["热点评论", "短图文", "事件追踪", "话题互动", "品牌营销", "明星动态"],
    title_max_length=140,
    body_max_length=2000,
    tags_max_count=3,
    style_guide=(
        "微博风格：短平快、有态度、善用话题#、"
        "紧跟热点、互动性强、适当用emoji。"
        "微博正文就是标题，140字内说清。"
    ),
    hot_patterns=["热搜评论", "话题互动", "事件追踪", "观点输出", "品牌营销"],
    templates=[
        ContentTemplate(
            name="热点评论",
            template_type=TemplateType.COPYWRITING,
            platform="weibo",
            description="微博热点评论模板",
            structure="观点+论据+话题标签",
            example=(
                "{核心观点}。\n\n"
                "{论据/分析}。\n\n"
                "{互动引导}？\n\n"
                "#{话题1} #{话题2} #{话题3}"
            ),
            tips=["观点要鲜明不模棱两可", "140字以内效果最好", "带1-3个话题标签", "结尾抛问题引导评论"],
            variables=["核心观点", "论据/分析", "互动引导", "话题1-3"],
        ),
        ContentTemplate(
            name="标签策略",
            template_type=TemplateType.TAGS,
            platform="weibo",
            description="微博话题标签策略",
            structure="1个热门话题+1-2个细分话题",
            example=(
                "#{热搜话题} #{细分话题} #{品牌/事件}"
            ),
            tips=["1个热门话题引流", "1-2个细分话题精准", "话题不超过3个", "参与微博官方话题活动"],
            variables=["热搜话题", "细分话题", "品牌/事件"],
        ),
    ],
)


WECHAT = PlatformConfig(
    id="wechat",
    name="微信公众号",
    icon="💚",
    description="深度阅读平台，品牌与私域阵地",
    content_types=["深度长文", "品牌推文", "行业分析", "教程攻略", "人物故事", "产品发布"],
    title_max_length=64,
    body_max_length=20000,
    tags_max_count=5,
    style_guide=(
        "公众号风格：深度专业、排版美观、段落简短、"
        "善用小标题、图文并茂、结尾引导关注/转发。"
        "标题决定打开率，封面决定点击率。"
    ),
    hot_patterns=["深度解读", "行业分析", "教程攻略", "品牌故事", "人物专访"],
    templates=[
        ContentTemplate(
            name="深度长文",
            template_type=TemplateType.COPYWRITING,
            platform="wechat",
            description="公众号深度文章模板",
            structure="引子→核心论点→分章节论证→案例/数据→总结→行动号召",
            example=(
                "# {标题}\n\n"
                "{引子段落——用故事/数据/问题开场}\n\n"
                "---\n\n"
                "## 01 {章节1标题}\n\n"
                "{章节1内容}\n\n"
                "> {引用/金句}\n\n"
                "## 02 {章节2标题}\n\n"
                "{章节2内容}\n\n"
                "## 03 {章节3标题}\n\n"
                "{章节3内容}\n\n"
                "---\n\n"
                "### 写在最后\n\n"
                "{总结与观点}\n\n"
                "---\n\n"
                "如果这篇文章对你有启发，欢迎转发分享。\n"
                "关注「{公众号名}」，获取更多{领域}深度内容。"
            ),
            tips=[
                "标题决定60%的打开率",
                "开头300字决定读者是否继续",
                "每段不超过3-4行",
                "小标题让文章结构清晰",
                "金句/引用增加分享率",
                "结尾引导关注和转发",
            ],
            variables=["标题", "引子段落", "章节1-3标题", "章节1-3内容", "引用/金句", "总结与观点", "公众号名", "领域"],
        ),
        ContentTemplate(
            name="标题模板",
            template_type=TemplateType.TITLE,
            platform="wechat",
            description="公众号高打开率标题公式",
            structure="好奇心/价值感+关键词",
            example=(
                "① {数字}年{领域}老兵：{观点}\n"
                "② {主题}的{数字}层境界，你在第几层？\n"
                "③ 深度｜{主题}背后，{洞察}\n"
                "④ {事件}给我们{数字}个启示\n"
                "⑤ 为什么{现象}？{数字}个你不知道的原因"
            ),
            tips=["64字以内", "前14字最关键", "数字增加打开率", "适当用「深度」「解析」等词", "避免纯标题党影响信任"],
            variables=["数字", "领域", "观点", "主题", "洞察", "事件", "现象"],
        ),
        ContentTemplate(
            name="封面文案",
            template_type=TemplateType.COVER,
            platform="wechat",
            description="公众号封面配文模板",
            structure="大标题+副标题/标签",
            example=(
                "主标题：{核心关键词}\n"
                "副标题：{补充说明}/{数字}个{类别}\n"
                "风格：{风格建议}（简约/商务/文艺）"
            ),
            tips=["封面文字不超过10字", "品牌色调统一", "大字+留白最有效"],
            variables=["核心关键词", "补充说明", "数字", "类别", "风格建议"],
        ),
    ],
)


# ── 平台注册表 ──────────────────────────────────────────────────


PLATFORMS: dict[str, PlatformConfig] = {
    "xiaohongshu": XIAOHONGSHU,
    "douyin": DOUYIN,
    "kuaishou": KUAISHOU,
    "bilibili": BILIBILI,
    "zhihu": ZHIHU,
    "toutiao": TOUTIAO,
    "weibo": WEIBO,
    "wechat": WECHAT,
}


def get_platform_config(platform_id: str) -> PlatformConfig:
    """获取平台配置

    Args:
        platform_id: 平台 ID（如 'xiaohongshu', 'douyin' 等）

    Returns:
        PlatformConfig 实例

    Raises:
        ValueError: 平台不存在
    """
    if platform_id not in PLATFORMS:
        available = ", ".join(PLATFORMS.keys())
        raise ValueError(
            f"平台 '{platform_id}' 不存在，可用平台: {available}"
        )
    return PLATFORMS[platform_id]


def list_platforms() -> list[dict[str, str]]:
    """列出所有支持的平台

    Returns:
        平台信息列表，每项包含 id、name、icon
    """
    return [
        {"id": p.id, "name": p.name, "icon": p.icon, "description": p.description}
        for p in PLATFORMS.values()
    ]
