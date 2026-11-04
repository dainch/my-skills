# 连续生产状态机

## 1. 运行模式

- `direct`：用户给定主题和充分素材，直接进入诊断、写作与审稿。
- `continuous`：自动完成选题、研究、写作、封面、审稿和发布包，正常路径止于 `ready`。
- `outline_first`：用户明确要求先看提纲或脚本骨架时暂停。

用户未指定且要求“全程代做、连续完成、自动选题”时，使用 `continuous`。

## 2. 状态流

内部运行状态：

```text
planned -> researching -> evidence_ready -> drafting -> reviewing -> ready_for_publish
```

异常出口：

- `needs_material`：缺少完成主题所需的基础素材。
- `needs_source_confirmation`：关键事实只来自未确认候选资料。
- `needs_sensitive_review`：存在项目、人员、坐标、合同、原始数据或高风险公开边界。
- `failed`：检索、文件生成或校验命令真实失败。

Output frontmatter 只使用仓库允许的流程状态：

```text
draft -> reviewing -> ready -> published
```

不要把内部异常状态写成 Wiki 生命周期，也不要使用 `summarized`、`compiled`、`stale`、`conflicted` 或 `archived`。

## 3. 连续执行规则

1. 完成选题评分并选择最高分且证据可满足的主题。
2. 完成本地 Brain-First 查询，再按需调用公网研究。
3. 建立来源账本，区分事实证据与结构参考。
4. 关键事实可追溯后生成 `status: draft` 成稿和封面。
5. 进入 `status: reviewing`，执行全部审稿门禁。
6. 所有硬门禁通过后改为 `status: ready`，生成发布清单。

其中第 5-6 步必须依次通过 `output_guard.py --strict`、`validate_wechat_article.py` 和 `validate_publish_manifest.py`。正文中的专业数字或行动阈值必须有 `claim_evidence`；发布清单校验退出码为 `0` 后，才可写入 `ready`。
7. 停止，不调用草稿箱或正式发布接口。

不得为了保持连续运行而跳过证据、敏感信息、版权或合规门禁。正常路径可以只在最终发布时人工操作；异常路径必须暂停并报告精确缺口。

## 4. 文件边界

- 选题与候选资料维护在 `600-Output/00-Content-Plan/`。
- 正式文章、视频脚本和联动成品维护在 `600-Output/01-WeChat/`。
- 主封面维护在 `Attachments/`。
- 不自动修改 `100-Raw/`，不自动摄取 `300-Wiki/`，不自动发布。
- `published` 只能在用户确认实际发布后写入。
