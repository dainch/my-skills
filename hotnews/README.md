# hotnews

关键词驱动热点收集器 + 确定性 Markdown 渲染器。零第三方依赖（仅 Python 标准库）。

## 为什么不用现成聚合器

这个包把「抓取」和「格式化」彻底分开：

```
collect   → 脚本抓原始信号，落盘 raw.json（确定性）
interpret → 调用它的 Agent 读 raw.json，填 interpret.json（语义）
render    → 脚本把 interpret.json 强制渲染成最终 .md（确定性）
```

格式的唯一真源在 `render.py`，不在任何 Markdown 模板文件里。所以同一份
interpret.json 在任何机器、任何模型手里都产出逐字节一致的输出。

## 安装

```bash
uvx --from git+https://github.com/<owner>/<repo>.git#subdirectory=.agents/skills/hotnews hotnews --help
```

或本地开发：

```bash
uv run --project .agents/skills/hotnews hotnews --help
```

## 用法

```bash
# 1. 收集（省略 --out 则落在系统临时目录，不污染当前目录）
hotnews collect --keywords "AI大模型,岩土工程"

# 2. 查看 Agent 需要填写的字段
hotnews schema

# 3. （Agent 生成 interpret.json 之后）渲染
#    省略 --out 时产物固定为 每日热点-YYYY-MM-DD.md（不含关键词）
hotnews render --data /tmp/hotnews-xxxx/interpret.json

# 也可以全程用管道，中间件不落盘
hotnews render --data - < interpret.json
```

## 文件命名

`render` 的输出文件名只由日期字段决定：`每日热点-YYYY-MM-DD.md`。
关键词不进文件名——关键词长短、个数、语言都不影响产物路径。
同名文件已存在时直接覆盖并在 stderr 提示；同日多期请显式指定 `--out`。

`collect` 和 `render` 的过程文件（`raw.json`、`interpret.json`）属于中间件，
默认写系统临时目录，不需要保留；用 `--out -` / `--data -` 可完全不经磁盘。

## 环境变量

| 变量 | 说明 |
| :--- | :--- |
| `HOTNEWS_PROXY` | HTTP 代理，如 `http://127.0.0.1:7890`。访问 Reddit 时需要。 |
| `HOTNEWS_EXA_ENDPOINT` | 覆盖 Exa MCP 端点，默认 `https://mcp.exa.ai/mcp` |
| `HOTNEWS_GITHUB_TOKEN` | 提升 GitHub Search 限额（未设置时 10 次/分钟） |

## 信源

| 源 | 方式 | 认证 |
| :--- | :--- | :--- |
| `hackernews` | Algolia Search API | 无需 |
| `github` | GitHub Search API | 可选 token |
| `reddit` | `/search.json` | 无需，易 429 |
| `rss` | 36kr / TechCrunch / Product Hunt / dev.to | 无需 |
| `v2ex` | `/api/topics/hot.json` | 无需 |
| `wechat` | Exa 公开 MCP 端点 | 无需 |

GitHub 条目的 `title` 只写 `owner/repo`，星数进 `extra.stars`（渲染为热度），仓库描述进 `summary`。

每个源独立降级：失败不会中断整体收集，状态写入 raw.json 的 `sources[].status`
（`ok` / `no_hit` / `degraded` / `unavailable`），渲染时如实呈现。
`no_hit` 表示路由正常但零命中，与路由异常严格分开。

## 测试

```bash
python -m unittest discover -s tests -v
```

21 个用例覆盖渲染器的硬约束：`null` 字段整行省略、`heat` 缺失也省略、
`no_hit` 与路由异常区分、校验错误一次性全量报告。
不覆盖网络抓取（依赖外部服务，结果不可复现）。

## 已知限制

- Exa 公开端点不支持日期过滤，微信条目的 `published_at` 多为 `null`。渲染器会省略该行，不伪造时间。
- `items[].summary` 来自各源原始描述：HN `story_text`（纯链接帖为空）、GitHub `description`、
  RSS `description` / `content:encoded`、V2EX `content`、Exa 正文，统一去标签后截到 200 字。
  源本身没给正文时仍为 `null`。
- Reddit 在无代理环境下大概率 429，属预期降级。
- 关键词过多时会触发 GitHub 未认证限额。

## License

MIT
