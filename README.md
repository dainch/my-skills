# my-skills

面向中文专业场景的 Agent 技能集合：**法律实务 · 工程技术 · 内容生产**。

6 个互相独立的 skill，统一采用 `SKILL.md`（YAML frontmatter 声明 `name` / `description`）+ 按需读取的 `references/` 渐进披露结构，可被任何按该约定加载技能的 agent 直接使用（如 Claude Code、pi）。

## 技能一览

| 技能 | 领域 | 一句话用途 | 触发示例 |
|---|---|---|---|
| [civil-code](civil-code/) | 法律 · 法条检索 | 民法典全 1260 条结构化检索，返回**逐字原文**与编/章/条号定位 | 「民法典第 577 条怎么规定」 |
| [claim-chart](claim-chart/) | 法律 · 要件分析 | 专利权利要求对照表 / 民事构成要件分析表，每格附精确引用，**缺口检测优先** | 「我们证明这项主张还缺什么」 |
| [loan-defense](loan-defense/) | 法律 · 应诉实务 | 网贷/金融借款纠纷「场景 → 打法」库 | 「收到网贷平台起诉怎么办」 |
| [engineering-review-ppt](engineering-review-ppt/) | 工程技术 · 汇报 | 桥梁/隧道/土木评审汇报 PPT 五阶段生产线 | 「做施工图评审汇报 PPT」 |
| [wechat-content-studio](wechat-content-studio/) | 内容生产 | 公众号文章 / 视频号视频 / 图文联动全程代做，含封面生成与发布前硬门禁 | 「公众号全程代做」「图文联动」 |
| [hotnews](hotnews/) | 信息采集 | 关键词驱动热点收集 + 确定性 Markdown 日报渲染 | 「收集热点」「生成 briefing」 |

---

## 各技能说明

### civil-code —— 民法典法条检索

按「编 → 分编 → 章 → 节 → 条」组织民法典全部条文，覆盖总则、物权、合同、人格权、婚姻家庭、继承、侵权责任、附则八编；另附 `cheatsheet.md`（速查）、`glossary.md`（术语）、`patterns.md`（常见引用模式）。

- **边界**：只给法条原文与结构索引，**不下结论、不做法律评价**。
- **来源纪律**：引用标注 `[法条原文]`，以 2020-05-28 通过、2021-01-01 施行版本为准，并提示核对时效与司法解释。
- **入口**：`SKILL.md` → `config/CLAUDE.md`（角色与引用纪律）→ `references/0X-*.md`（分编条文）。

### claim-chart —— 要件分析表

两种模式：专利（侵权 / 无效 / 审查）与民事（任何诉讼请求或抗辩）。输出为逐要件映射表，每格附精确引用，并把**缺口**作为首要产出而非附带结论。

- `references/element-templates.md`：要件模板
- `references/evidence-rules-core.md`：证据规则
- `references/civil-procedure-core.md`：民诉法核心
- `config/CLAUDE.md`：实践级默认值（当事人角色、保密标头、来源溯源标签）

### loan-defense —— 网贷应诉打法

按「场景 → 打法」组织：暴力/违规催收、微信支付宝账户冻结（财保 vs 执保）、法院支付令、网贷仲裁（先予/网络/虚假）、平台起诉、债权转让后起诉、征信代偿、信用卡退费、1068 骚扰短信、利息发票进项。每场景含判断信号、应诉步骤、法律依据、话术与文书、注意事项，并附证据清单、通用抗辩武器库、风险红线，以及源笔记的修正与待核实清单。

### engineering-review-ppt —— 工程评审汇报 PPT

五阶段生产线：确认输入 → 取材建素材库 → 大纲与配色定调 → 逐页生成 → 校验交付。三条硬规则：**数据唯一源**（只取设计图纸原件）、**成果为纲**（观众看得懂才算完成）、**图片 > 表格 > 短句**。

- `references/production-standard.md`：制作规范与配色体系
- `references/outline-template.md`：18 页章节骨架
- `references/cjk-pitfalls.md`：中文字体与排版坑位

### wechat-content-studio —— 微信内容工作室

从周计划、知识库、网络检索或用户素材出发，完成选题评分、资料研究、来源账本、正文、封面（固定 2.35:1）、视频脚本、多轮审稿，最终产出发布前交付包。

- 15 个 `references/`：编辑规则、投喂模板（文章/视频/联动）、研究流水线、审稿规则、发布硬门禁、推荐运营合规、连续生产状态机、输出包规范
- `scripts/create_wechat_cover.py`：生成 2.35:1 封面 PNG（依赖 Pillow + 系统中文字体）
- `scripts/validate_wechat_article.py`、`scripts/validate_publish_manifest.py`：正文与发布清单校验（零依赖，仅标准库）
- `agents/openai.yaml`：界面元数据

默认只推进到 `status: ready`，**不会**自动标记 `published` 或调用正式发布接口。

### hotnews —— 关键词热点日报

把「抓取」与「格式化」分开，保证输出可复现：

```
collect   → 脚本抓原始信号，落盘 raw.json（确定性）
interpret → 调用它的 Agent 读 raw.json，填 interpret.json（语义）
render    → 脚本把 interpret.json 强制渲染成最终 .md（确定性）
```

格式的唯一真源在 `src/hotnews/render.py`，不在任何 Markdown 模板里——同一份 `interpret.json` 在任何机器、任何模型手里产出逐字节一致的输出。零第三方依赖，仅 Python 标准库。

```bash
hotnews collect --keywords "隧道,边坡" --hours 24 --limit 20   # → raw.json
# Agent 读 raw.json，产出 interpret.json
hotnews render --data interpret.json --output daily.md
hotnews schema                                                 # 打印 interpret.json 契约
```

---

## 目录结构

```
.
├── civil-code/
│   ├── SKILL.md
│   ├── cheatsheet.md / glossary.md / patterns.md
│   ├── config/CLAUDE.md
│   └── references/01-总则.md … 08-附则.md
├── claim-chart/
│   ├── SKILL.md
│   ├── config/CLAUDE.md
│   └── references/{element-templates,evidence-rules-core,civil-procedure-core}.md
├── loan-defense/
│   ├── SKILL.md
│   ├── config/CLAUDE.md
│   └── references/knowledge-base.md
├── engineering-review-ppt/
│   ├── SKILL.md
│   └── references/{production-standard,outline-template,cjk-pitfalls}.md
├── wechat-content-studio/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── references/            # 16 个规则与模板
│   ├── scripts/               # 封面生成 + 两个校验器
│   └── tests/
└── hotnews/
    ├── SKILL.md  README.md  pyproject.toml
    ├── references/interpret-schema.md
    ├── src/hotnews/           # cli / collectors / http / models / render
    └── tests/
```

## 安装

把需要的技能目录复制或软链到你的 agent 的 skills 目录即可，例如：

```bash
# 全局（Claude Code / pi 等）
cp -r civil-code ~/.claude/skills/
ln -s "$PWD/claim-chart" ~/.pi/agent/skills/claim-chart

# 项目内
cp -r hotnews <your-project>/.agents/skills/
```

`hotnews` 也可以直接从本仓库运行，无需 clone：

```bash
uvx --from "git+https://github.com/dainch/my-skills.git#subdirectory=hotnews" hotnews schema
```

## 环境与依赖

| 项 | 要求 | 涉及的技能 |
|---|---|---|
| Python | 3.9+ | hotnews、wechat-content-studio 脚本 |
| uv / uvx | 可选，用于免安装运行 hotnews | hotnews |
| Pillow | 生成封面时需要 | wechat-content-studio |
| 中文字体 | `create_wechat_cover.py` 默认读取 `C:\Windows\Fonts` 下的微软雅黑/等线/黑体/思源黑体；其他系统需改脚本中的字体路径或传 `--background` | wechat-content-studio |
| `HOTNEWS_PROXY` | 可选，如 `http://127.0.0.1:7890`，访问 Reddit 时需要 | hotnews |

`civil-code`、`claim-chart`、`loan-defense`、`engineering-review-ppt` 为纯 Markdown 技能，无运行时依赖。

## 自检

两个带测试的技能均可离线运行：

```bash
cd hotnews                && python -m unittest discover -s tests -q   # 28 tests
cd wechat-content-studio  && python -m unittest discover -s tests -q   # 8 tests
```

## 共同设计约定

1. **单一入口**：每个技能只有一个 `SKILL.md`，frontmatter 的 `description` 决定何时被触发。
2. **渐进披露**：`SKILL.md` 只给流程骨架，细则放在 `references/`，按任务类型按需读取，避免一次性灌满上下文。
3. **可裁剪的实践配置**：`config/CLAUDE.md` 存角色、默认值、来源标签等实践级设定；文件缺失时回退内置默认，不阻断执行。
4. **确定性与语义分离**：凡是能被脚本确定性完成的部分（渲染、校验、封面、抓取）都写成 `scripts/`；只把判断题留给模型。
5. **不自作主张**：涉及发布、结论、事实认定时默认停在待确认状态。

## 免责声明

- `civil-code`、`claim-chart`、`loan-defense` 提供的是条文原文、要件结构与实务打法参考，**不构成法律意见**，也不能替代执业律师针对具体案件作出的判断。条文时效、司法解释与地方裁判口径请自行核对。
- `engineering-review-ppt` 提供的是制作流程与排版规范，工程数据的正确性由设计图纸原件与使用者负责。
- `wechat-content-studio` 只产出待发布包，不代为发布；发布前请自行完成事实核验与合规检查。

## 许可证

本仓库整体采用 [MIT 许可证](LICENSE)（`Copyright (c) 2026 dainch`），`hotnews` 子目录保持一致（见 `hotnews/pyproject.toml`）。

```
MIT License  Copyright (c) 2026 dainch
```

需注意：许可证覆盖的是本仓库的**文本与代码本身**，不改变其内容性质——法条原文请以官方发布版本为准，技术流程与实务打法仍需使用者自行承担责任（见上节免责声明）。
