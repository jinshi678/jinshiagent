# 内容创作使用教程

JinshiAgent 内置了专业的内容创作模块，支持 8 大主流自媒体平台的一键内容生成。

## 快速开始

### 1. 查看支持的平台

```
/平台列表
```

输出：
```
📋 支持的自媒体平台：

  📕 小红书（xiaohongshu）— 种草社区，生活方式分享平台
  🎵 抖音（douyin）— 短视频平台，强娱乐属性
  🎬 快手（kuaishou）— 短视频社区，接地气、真实感
  📺 B站（bilibili）— 年轻人文化社区，知识+兴趣
  💡 知乎（zhihu）— 知识问答社区，深度内容平台
  📰 今日头条（toutiao）— 资讯分发平台，兴趣推荐驱动
  🔥 微博（weibo）— 社交媒体平台，热点话题发源地
  💚 微信公众号（wechat）— 深度阅读平台，品牌与私域阵地
```

### 2. 一键生成全套素材

```
/创作 <平台> <主题>
```

示例：
```
/创作 douyin AI绘画入门
/创作 xiaohongshu 平价护肤好物
/创作 bilibili Python爬虫教程
```

生成内容包含：
- 📝 标题
- 📄 脚本/文案
- 🏷️ 标签
- 🖼️ 封面文案
- 💡 创作建议

### 3. 批量选题

```
/选题 <平台> <领域>
```

示例：
```
/选题 xiaohongshu 美妆护肤
/选题 douyin 知识科普
/选题 bilibili 编程教程
```

### 4. 单项生成

```
/标题 <平台> <主题>     → 仅生成标题
/脚本 <平台> <主题>     → 仅生成视频脚本
/文案 <平台> <主题>     → 仅生成文案
/标签 <平台> <主题>     → 仅生成标签策略
/封面 <平台> <主题>     → 仅生成封面文案
```

### 5. 多平台适配

```
/多平台 AI绘画工具推荐
```

同一主题，自动适配 8 个平台的内容风格。

---

## 完整指令列表

| 指令 | 别名 | 说明 |
|------|------|------|
| `/创作 <平台> <主题>` | `/全套`, `/一键` | 一键生成全套创作素材 |
| `/选题 <平台> <领域>` | `/策划`, `/批量` | 批量产出选题方向 |
| `/标题 <平台> <主题>` | — | 仅生成标题 |
| `/脚本 <平台> <主题>` | — | 仅生成视频脚本 |
| `/文案 <平台> <主题>` | — | 仅生成文案 |
| `/标签 <平台> <主题>` | — | 仅生成标签策略 |
| `/封面 <平台> <主题>` | — | 仅生成封面文案 |
| `/多平台 <主题>` | `/全平台` | 同一主题适配多平台 |
| `/平台列表` | `/平台` | 查看支持的平台 |

---

## 平台 ID 对照表

| 平台 | ID | 特点 |
|------|-----|------|
| 小红书 | `xiaohongshu` | 种草笔记、生活分享 |
| 抖音 | `douyin` | 短视频、3秒钩子 |
| 快手 | `kuaishou` | 接地气、生活化 |
| B站 | `bilibili` | 知识科普、中长视频 |
| 知乎 | `zhihu` | 深度图文、专业回答 |
| 今日头条 | `toutiao` | 资讯解读、热点追踪 |
| 微博 | `weibo` | 热点评论、短图文 |
| 微信公众号 | `wechat` | 深度长文、品牌推文 |

---

## API 调用方式

### 一键生成全套素材

```bash
curl -X POST http://localhost:8000/creation/bundle \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AI绘画入门",
    "platform": "douyin"
  }'
```

### 批量选题

```bash
curl -X POST http://localhost:8000/creation/topics \
  -H "Content-Type: application/json" \
  -d '{
    "niche": "AI工具",
    "platform": "xiaohongshu",
    "count": 5
  }'
```

### 单项生成

```bash
curl -X POST http://localhost:8000/creation/single \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "ChatGPT使用技巧",
    "platform": "bilibili",
    "template_type": "title"
  }'
```

### 多平台适配

```bash
curl -X POST http://localhost:8000/creation/multi-platform \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AI绘画工具推荐",
    "platforms": ["douyin", "xiaohongshu", "bilibili"]
  }'
```

### Python SDK 调用

```python
from jinshiagent.creation import ContentGenerator, get_platform_config

# 初始化生成器（需要 LLM 客户端）
from jinshiagent.llm import LLMClient, LLMConfig
llm = LLMClient(LLMConfig(api_key="sk-xxx"))

gen = ContentGenerator(llm_client=llm)

# 一键生成
bundle = gen.generate_bundle(
    topic="AI绘画入门",
    platform="douyin",
)
print(f"标题: {bundle.title}")
print(f"脚本: {bundle.script}")
print(f"标签: {bundle.tags}")

# 批量选题
topics = gen.generate_topics(
    niche="AI工具",
    platform="xiaohongshu",
    count=5,
)
for t in topics.topics:
    print(f"选题: {t['title']}")

# 多平台适配
bundles = gen.generate_multi_platform(topic="AI绘画工具推荐")
for b in bundles:
    print(f"{b.platform_name}: {b.title}")

# 无 LLM 时获取 prompt（供外部调用）
gen_no_llm = ContentGenerator()
prompt = gen_no_llm.generate_single(
    topic="AI绘画入门",
    platform="douyin",
    template_type=TemplateType.TITLE,
)
# prompt 是构建好的 prompt 文本，可传给任何 LLM
```

---

## 创作工作流建议

### 日常内容生产流程

1. **周一**：使用 `/选题` 批量生成本周选题
2. **每日**：使用 `/创作` 生成当天内容的全套素材
3. **发布前**：使用 `/标题` 和 `/标签` 微调标题和标签
4. **跨平台**：使用 `/多平台` 适配不同平台发布

### 选题策划流程

1. 确定赛道/领域
2. `/选题 <平台> <赛道>` 获取选题方向
3. 从选题中选择最合适的 3-5 个
4. 逐个 `/创作 <平台> <选题>` 生成完整素材

### 爆款标题优化

1. `/标题 <平台> <主题>` 生成 5 个标题选项
2. A/B 测试选择最佳标题
3. 也可以 `/多平台 <主题>` 看不同平台适合什么风格

---

## 各平台创作要点

### 小红书 📕

- **标题**：20字以内，数字+对比+悬念
- **正文**：口语化、多用emoji、分段清晰
- **标签**：5-10个，大词+长尾词
- **封面**：大字标题+产品图

### 抖音 🎵

- **开头**：3秒定生死，制造悬念
- **节奏**：每个片段不超过10秒
- **台词**：短句、一句一画面
- **结尾**：引导评论+关注

### 快手 🎬

- **风格**：接地气、真实不做作
- **称呼**：「老铁」「家人」
- **内容**：生活化场景、正能量

### B站 📺

- **信息量**：密度高但不枯燥
- **节奏**：适当玩梗、弹幕友好
- **结构**：分章节、有小标题
- **结尾**：三连+下期预告

### 知乎 💡

- **结论先行**：第一句话给明确答案
- **数据支撑**：引用来源增加可信度
- **案例**：具体且有代入感

### 今日头条 📰

- **时效性**：紧跟热点
- **数据**：用数字增加信息量
- **观点**：多角度、保持中立

### 微博 🔥

- **短平快**：140字以内
- **话题**：带1-3个#话题#
- **互动**：结尾抛问题引导评论

### 微信公众号 💚

- **标题**：前14字决定打开率
- **开头**：300字决定是否继续阅读
- **排版**：段落简短、图文并茂
- **结尾**：引导关注+转发
