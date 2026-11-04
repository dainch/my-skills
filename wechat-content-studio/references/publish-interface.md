# 发布接口契约

## 1. 默认行为

只准备发布包，不连接公众号凭据，不推送草稿箱，不正式发布。最终状态为 `ready`；用户确认实际发布后才能改为 `published`。

每篇待发布文章生成 `主题-发布清单-YYMMDD.json`：

```json
{
  "schema_version": 2,
  "status": "ready",
  "output_profile": "publish_article",
  "title": "文章标题",
  "summary": "文章摘要",
  "body_path": "600-Output/01-WeChat/主题-YYMMDD.md",
  "cover": {
    "path": "Attachments/主题-公众号封面-YYMMDD.png",
    "width": 2350,
    "height": 1000
  },
  "source_refs": [
    "[[300-Wiki/01-Professional/示例]]"
  ],
  "claim_evidence": [
    {
      "line": 42,
      "claim": "正文中的专业数字或行动阈值",
      "source_ref": "[[300-Wiki/01-Professional/示例]]",
      "support": "该来源明确支持这一数值及其适用条件",
      "status": "verified"
    }
  ],
  "review": {
    "facts": "pass",
    "source_traceability": "pass",
    "sensitivity": "pass",
    "compliance": "pass",
    "title_body_cover": "pass",
    "output_schema": "pass"
  },
  "publisher": {
    "mode": "manual",
    "enabled": false,
    "adapter": null,
    "action": "none"
  }
}
```

路径相对于知识库根目录。清单不得包含 `appid`、`app_secret`、访问令牌、Cookie 或其他凭据。

## 2. 校验

在知识库根目录运行：

```bash
python -X utf8 .agents/skills/wechat-content-studio/scripts/validate_publish_manifest.py path/to/manifest.json
```

校验器会重新打开 `body_path` 执行正文硬门禁，并要求每个检测到的专业数字或行动阈值都有对应行号的 `claim_evidence`。`source_ref` 必须同时存在于顶层 `source_refs`；没有此类声明时使用空数组。

只有退出码为 `0` 时，发布包才可声明 `ready`。

## 3. 预留适配器

未来发布适配器只实现以下接口，不改变本 skill 的默认行为：

```text
validate(manifest) -> validation_result
prepare_draft(manifest) -> remote_draft_id
publish(remote_draft_id, explicit_approval) -> publish_result
```

- `validate` 可自动执行。
- `prepare_draft` 默认禁用，启用前需用户明确授权和独立凭据配置。
- `publish` 必须检查当次显式授权，不能继承历史授权或由定时任务自动触发。
- 凭据只从环境变量或安全凭据存储读取，不写入 skill、Output 或发布清单。
