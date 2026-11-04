# interpret.json 字段详解

## 完整示例

```json
{
  "date": "2026-11-04",
  "window": "过去 24 小时",
  "generated_at": "2026-11-04 12:00",
  "source_status": {
    "hackernews": "ok",
    "github": "ok",
    "reddit": "degraded",
    "rss": "ok",
    "v2ex": "no_hit",
    "wechat": "unavailable"
  },
  "sections": [
    {
      "name": "AI 与大模型",
      "items": [
        {
          "title": "某机构发布开源推理模型",
          "url": "https://example.com/article",
          "platform": "Hacker News",
          "published_at": "2026-11-04 05:40",
          "content_type": "产品发布",
          "heat": "HN 312 分 · 84 评论",
          "summary": "该模型在 MMLU 上报告 82.3 分，权重以 Apache-2.0 发布。",
          "significance": "若第三方复现成立，将改变本地部署的成本结构。"
        },
        {
          "title": "讨论：LLM 是否已经饱和",
          "url": "https://news.ycombinator.com/item?id=123",
          "platform": "Hacker News",
          "published_at": null,
          "content_type": "社区讨论",
          "summary": null,
          "significance": "分歧集中在基准测试的有效性上，值得跟踪后续实证。"
        }
      ]
    },
    {
      "name": "岩土工程",
      "items": []
    }
  ]
}
```

渲染结果：

```markdown
# 每日热点 2026-11-04

资料说明：生成时间 2026-11-04 12:00；时间窗口 过去 24 小时；信源状态：hackernews ok、github ok、reddit degraded、rss ok、v2ex no_hit、wechat unavailable（degraded/unavailable 为路由异常，不代表该平台无内容）；共 2 条，覆盖 2 个主题。

## AI 与大模型

### 1. 某机构发布开源推理模型

- 来源平台：Hacker News
- 发布时间：2026-11-04 05:40
- 内容类型：产品发布
- 热度：HN 312 分 · 84 评论
- 摘要：该模型在 MMLU 上报告 82.3 分，权重以 Apache-2.0 发布。
- 判断：若第三方复现成立，将改变本地部署的成本结构。
- 链接：[https://example.com/article](https://example.com/article)

### 2. 讨论：LLM 是否已经饱和

- 来源平台：Hacker News
- 内容类型：社区讨论
- 判断：分歧集中在基准测试的有效性上，值得跟踪后续实证。
- 链接：[https://news.ycombinator.com/item?id=123](https://news.ycombinator.com/item?id=123)

## 岩土工程

（本主题今日无命中条目）

<!-- rendered by hotnews 0.1.0 -->
```

注意第 2 条：`published_at` 和 `summary` 都是 `null`，渲染器**整行省略**，
不补"未知"，不补"N/A"。这是本技能区分于普通摘要工具的关键行为。

`heat` 同理：源没给互动数字段就写 `null`，行被省略。不要在 312 分上自己加个
"很火"之类的形容词，也不要估算。

`summary` 的原始素材在 `raw.json` 的 `items[].summary`：采集层会去标签、反转义、
压空白后截到 200 字（HN `story_text`、GitHub `description`、RSS `description` /
`content:encoded`、V2EX `content`、Exa 正文）。写成 1–2 句事实即可；该字段为空说明
信源真的没给正文，此时写 `null`，不要拿标题改写成摘要。

## 字段表

### 顶层

| 字段 | 必填 | 类型 | 说明 |
| :--- | :--- | :--- | :--- |
| `date` | 是 | string | `YYYY-MM-DD`，渲染进一级标题 |
| `sections` | 是 | array | 至少一个主题对象 |
| `window` | 否 | string | 时间窗口描述，进资料说明段 |
| `generated_at` | 否 | string | 生成时间，进资料说明段 |
| `source_status` | 否 | object | 键为信源名，值为 `ok` / `no_hit` / `degraded` / `unavailable` |

`no_hit` 与 `degraded`/`unavailable` 不可混用：前者表示路由正常但该平台在时间窗内
零条命中，后者表示路由异常。资料说明行会在出现 `degraded`/`unavailable` 时自动追加
一句说明，避免读者把路由故障当成"今日无内容"。

### section

| 字段 | 必填 | 类型 | 说明 |
| :--- | :--- | :--- | :--- |
| `name` | 是 | string | 主题名，渲染为二级标题 |
| `items` | 是 | array | 无命中时给空数组，渲染为"（本主题今日无命中条目）"。契约允许空数组，但编辑规则要求每主题 ≥3 条，零命中请勿建章节（见 SKILL.md §5.3） |

### item

| 字段 | 必填 | 类型 | 渲染为 |
| :--- | :--- | :--- | :--- |
| `title` | 是 | string | 三级标题 |
| `url` | 是 | string | 必须以 `http://` 或 `https://` 开头 |
| `platform` | 否 | string | `- 来源平台：` |
| `published_at` | 否 | string | `- 发布时间：` |
| `content_type` | 否 | string | `- 内容类型：` |
| `heat` | 否 | string | `- 热度：`，只搬 `items[].extra` 里的 points/comments/stars |
| `summary` | 否 | string | `- 摘要：` |
| `significance` | 否 | string | `- 判断：` |

## 校验行为

`hotnews render` 会先做全量校验再渲染，规则如下：

- `date` 不匹配 `YYYY-MM-DD` → 失败
- `sections` 为空数组 → 失败
- `url` 不以 `http://` / `https://` 开头 → 失败
- 选填字段给了非字符串、非 null 的值 → 失败
- `source_status` 出现 `ok`/`no_hit`/`degraded`/`unavailable` 之外的值 → 失败

失败时退出码为 1，且**一次列出所有错误**，不需要反复试错。错误信息格式为
`路径: 原因`，例如：

```
sections[0].items[2].url: 必须以 http:// 或 https:// 开头
source_status.wechat: 只允许 degraded/no_hit/ok/unavailable，实际 "failed"
```

不属于渲染器校验范围、但必须遵守的编辑规则：全文 30–50 条，每个主题不少于 3 条
（凑不满就合入相邻主题），零命中不建空章节。

## 常见错误

| 错误写法 | 正确写法 | 原因 |
| :--- | :--- | :--- |
| `"published_at": "未知"` | `"published_at": null` | 渲染器会省略整行，不输出假值 |
| `"heat": "很火"` | `"heat": "HN 312 分 · 84 评论"` 或 `null` | `heat` 只搬互动数字，不写形容词 |
| `"summary": "可能是一次重要发布"` | `"significance": "可能是一次重要发布"` | 推测属于判断，不属于摘要 |
| `"url": "example.com/a"` | `"url": "https://example.com/a"` | 无协议的链接不可点 |
| `sections: []` | 至少一个主题 | 空日报没有信息量 |
