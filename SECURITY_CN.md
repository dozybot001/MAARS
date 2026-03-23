# 安全策略

中文 | [English](SECURITY.md)

[项目说明](README_CN.md) | [贡献指南](CONTRIBUTING_CN.md) | [行为准则](CODE_OF_CONDUCT_CN.md)

### 报告漏洞

如果你发现安全漏洞，请负责任地报告：

1. **不要**创建公开 issue
2. 直接邮件联系维护者，或使用 GitHub 的私密漏洞报告功能
3. 提供漏洞的清晰描述以及复现步骤

我们会在 48 小时内回复，并与你一起推动修复。

### API Key 安全

- 切勿将 `.env` 文件或 API key 提交到仓库
- 使用 `.env.example` 作为模板，其中不包含任何密钥
- `.gitignore` 已配置为排除 `.env` 和 `.env.*`

### 已知注意事项

- MAARS 会在 `gemini` 和 `agent` 模式下把用户输入发送给 Google Gemini API
- 研究产物会以纯文本文件形式保存在 `research/` 中
- SSE 接口当前不要求认证，设计目标是本地开发场景
