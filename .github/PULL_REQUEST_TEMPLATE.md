Please fill this out in English or Chinese.
请使用英文或中文填写。

## What does this PR do? | 这个 PR 做了什么？

Brief description of the change.
简要说明本次变更。

## Type | 类型

- [ ] Bug fix | 缺陷修复
- [ ] New feature | 新功能
- [ ] Refactoring | 重构
- [ ] Documentation | 文档
- [ ] New mode / tool / skill | 新模式 / 工具 / 技能

## Checklist | 检查清单

- [ ] Pipeline layer remains mode-agnostic (no mock/gemini/agent imports in `pipeline/`) | Pipeline 层保持与模式无关（`pipeline/` 不引入 `mock/gemini/agent`）
- [ ] Tested with mock mode (`MAARS_LLM_MODE=mock`) | 已使用 mock 模式测试（`MAARS_LLM_MODE=mock`）
- [ ] Frontend has no build step (vanilla JS/CSS only) | 前端仍然无需构建步骤（仅原生 JS/CSS）
- [ ] No API keys or secrets in the commit | 提交中不包含 API key 或其他密钥
