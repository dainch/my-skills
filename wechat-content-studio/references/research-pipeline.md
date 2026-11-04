# 选题与资料研究

## 1. 检索顺序

按以下顺序工作，不得先搜公网再忽略本地知识：

1. 读取 `200-Maps/Index.md`、相关 MOC、Wiki 与 Sources。
2. 检查近期 `600-Output/01-WeChat/`，避免重复选题并保持系列口径。
3. 读取 `600-Output/00-Content-Plan/` 中的周计划、内容看板、关键词与候选资料。
4. 仍有选题或证据缺口时，调用 `agent-reach` 搜索公众号、官网、论文和公开案例。

不得扫描 `Important/`。`100-Raw/` 只读。未经用户确认，不把网络候选资料摄取到 `300-Wiki/`。

## 2. 自动选题

从周计划、SEO 关键词、历史内容缺口、评论问题和网络需求信号生成 3 到 8 个候选。每项按 0 到 5 分记录依据，再换算为百分制：

| 维度 | 权重 |
| --- | ---: |
| 账号与受众匹配 | 25 |
| 搜索需求或现场痛点 | 20 |
| 现有证据充足度 | 20 |
| 与历史内容的差异化 | 15 |
| 系列延展能力 | 10 |
| 合规与敏感风险可控性 | 10 |

- `>= 75`：可自动选为主选题。
- `60-74`：进入候选池，资料补齐后再选。
- `< 60`：本轮不采用。

不得虚构微信指数、阅读量或后台数据。无法取得真实需求数据时，明确写成“搜索需求推断”。

## 3. 公众号同题搜索

需要公网资料时，先按 `agent-reach` 做真实业务调用；`doctor` 只能作为预检，不能代替搜索成功证据。默认检索式：

- `{主题} site:mp.weixin.qq.com/s`
- `{主题} 案例 实操 site:mp.weixin.qq.com/s`
- `{主题} 规范 标准 site:mp.weixin.qq.com/s`
- `{长尾问题} site:mp.weixin.qq.com/s`

优先运行：

```powershell
& .agents/skills/wechat-content-studio/scripts/search_wechat_candidates.ps1 `
  -Topic "主题" `
  -LongTail "长尾问题1","长尾问题2" `
  -OutputPath "候选资料.json"
```

## 4. 候选资料契约

每条候选至少包含：

- `title`、`url`、`source_account`、`publish_date`
- `query`、`machine_summary`
- `source_role`：`demand_signal` / `structure_reference` / `case_candidate` / `evidence_candidate`
- `supported_claims`、`verification`、`risk_flags`
- `status`：自动发现时固定为 `candidate`

`verification` 使用 `search_result_only`、`opened_original`、`cross_checked`。状态与验真维度分开管理，不新增 `verified_candidate` 等平行状态。

## 5. 使用边界

- `search_result_only` 只能用于需求、标题、结构和案例线索，不能支撑确定性事实。
- 打开原文后仍需识别转载、营销表述、发布日期和原始出处。
- 工程参数、规范条文、政策、事故和高风险结论必须回到第一方或权威来源交叉验证。
- 公众号文章不得整段复制或改写规避检测，只提取可验证事实、结构启发和差异化空间。
- 写入 `Material-Inbox.md` 时保持 `candidate`；只有用户确认后才能变为 `saved` 或 `to_ingest`。
- 若关键事实仅有未确认网络候选，进入 `needs_source_confirmation`，不得继续生成 `ready` 成稿。
