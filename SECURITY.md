# Security Policy | 安全策略

## English

### Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public issue
2. **Email** the maintainers directly or use GitHub's private vulnerability reporting
3. Include a clear description of the vulnerability and steps to reproduce

We will respond within 48 hours and work with you to resolve the issue.

### API Key Safety

- Never commit `.env` files or API keys to the repository
- Use `.env.example` as a template — it contains no secrets
- The `.gitignore` is configured to exclude `.env` and `.env.*`

### Known Considerations

- MAARS sends user input to Google Gemini API (in `gemini` and `agent` modes)
- Research outputs are stored as plaintext files in `research/`
- The SSE endpoint does not require authentication (intended for local development)

---

## 中文

### 报告漏洞

如果你发现安全漏洞，请负责任地报告：

1. **不要**创建公开的 issue
2. 直接邮件联系维护者或使用 GitHub 的私密漏洞报告功能
3. 包含漏洞的清晰描述和复现步骤

我们将在 48 小时内回复并与你合作解决问题。

### API Key 安全

- 切勿将 `.env` 文件或 API key 提交到仓库
- 使用 `.env.example` 作为模板 — 其中不包含密钥
- `.gitignore` 已配置排除 `.env` 和 `.env.*`
