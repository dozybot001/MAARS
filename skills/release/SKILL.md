---
name: release
description: MAARS 仓库专用发版流程。用于准备和发布 GitHub Release：检查工作区、对齐文档、分析自上个 tag 以来的改动、决定 semver 版本、执行验证、打 annotated tag、发布双语 release notes。触发词："发版"、"release"、"/release"。
---

# Release Skill

当用户说“发版”、“release”或“/release”时，按下面流程执行。

这份流程是 **MAARS 仓库定制版**，相对通用 release skill 做了这些收口：

- MAARS 当前没有根目录 `VERSION` 文件，默认以最近的 `vX.Y.Z` tag 作为 release 基线
- 发布前必须同时通过后端测试和前端构建
- 文档对齐要覆盖 `README.md`、`README_CN.md`、`.env.example`、`docs/ROADMAP.md`
- GitHub Release notes 默认双语，英文在前；中文部分放在 `---` 之后，并包在 `<details><summary>中文</summary> ... </details>` 里

release notes 模板放在：

- `references/release-notes-template.EN.md`
- `references/release-notes-template.CN.md`

## 仓库约定

- 版本标签使用 `vX.Y.Z`
- 默认从当前分支发布，不要硬编码 `main`
- 不要 force push
- 不要复用已存在 tag
- 如果验证失败，停止发版

## 流程

### 1. 确认发布目标

- 读取当前分支：`git branch --show-current`
- 找最近的语义化版本 tag：

```bash
git tag --sort=-v:refname | rg '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -n 1
```

- 如果没有 tag，把当前版本视为首个正式 release
- 如果用户已经指定版本，用用户给的版本
- 如果用户没指定版本，根据变更范围建议一个版本

版本建议规则：

- `major`: 破坏性变更、对外行为显著重构、兼容性需要重新认知
- `minor`: 新功能、可见能力增强、重要工作流升级
- `patch`: bug 修复、安全修复、文档/脚本小改进

如果建议版本存在明显歧义，先给出建议并请求确认，再继续创建 tag。

### 2. 检查工作区

运行：

```bash
git status --short
```

规则：

- 如果有未提交改动，先判断它们是否属于本次 release
- 属于本次 release 的改动，需要纳入本次发版提交
- 不属于本次 release 的改动，不要偷偷带上
- 绝不提交 `.env`、密钥、token、credentials 等敏感文件

### 3. 分析自上个 tag 以来的变化

如果存在上一个 tag，运行：

```bash
git log --oneline <prev_tag>..HEAD
git diff --stat <prev_tag>..HEAD
git diff <prev_tag>..HEAD -- README.md README_CN.md .env.example backend/ frontend/src/ tests/
```

如果不存在上一个 tag，改为检查当前完整历史和工作树。

重点判断：

- 用户可见变化是什么
- 是否有配置项变化
- 是否有运行命令、启动方式、发布方式变化
- 是否有破坏性变更
- 哪些点应该进入 release notes，哪些只是内部重构

### 4. 对齐发布相关文档

至少检查这些文件是否与代码一致：

- `README.md`
- `README_CN.md`
- `.env.example`
- `docs/ROADMAP.md`

按需补查：

- `docs/CN/architecture.md`
- 根目录 `SKILL.md`
- `skills/README.md`

重点核对：

- 技术栈描述
- 配置项说明
- 一键启动行为
- 当前 release 后用户能看到的新能力

如果文档不一致，先修文档，再发版。

### 5. 执行发布前验证

MAARS 仓库默认验证命令：

```bash
pytest tests/ -q
cd frontend && npm run build
```

如果本次发布改动明显影响启动链路、认证或发布流程，可补充：

```bash
bash start.sh
```

规则：

- 任一验证失败，停止发版
- 若在 rebase / pull 后代码变化，重新跑关键验证

### 6. 准备发布提交

- 把本次 release 相关改动整理成一笔 release-prep commit
- commit message 保持直接清晰，例如：

```text
chore: prepare release v11.1.0
```

不要把“顺手修的、但与本次 release 无关”的改动混进去。

### 7. 同步远端

基于当前分支执行：

```bash
BRANCH=$(git branch --show-current)
git pull --rebase origin "$BRANCH"
pytest tests/ -q
(cd frontend && npm run build)
git push origin "$BRANCH"
```

规则：

- push 被拒绝时，可在 pull --rebase 后重试一次
- 若出现 rebase 冲突，停止并告知用户

### 8. 创建并推送 tag

- 创建 annotated tag，不要 lightweight tag

```bash
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

发布前确认：

- tag 不存在于本地和远端
- 目标版本与 release notes 一致

### 9. 生成并发布 GitHub Release

先看一下上一个 release 的标题风格和正文密度：

```bash
gh release view <prev_tag>
```

然后创建新的 release。

正文规则：

- Release 标题单独放在 `--title`
- 英文在前
- 单独一行 `---`
- 中文部分放在 `<details>` 里，`<summary>` 默认写 `中文`
- 默认结构保持简短

要求：

- 只保留有真实内容的小节
- 不要在 Summary 和 Changes 里重复同一句话
- 如果有配置变化、破坏性变化或迁移注意事项，再加 `Notes / 说明`
- 中文部分默认复述英文要点，但允许更贴近中文读者表达，不必逐句直译

推荐命令形式：

```bash
gh release create vX.Y.Z --title "vX.Y.Z" --notes-file /tmp/maars-release-notes.md
```

### 10. 发布后核对

至少确认：

- GitHub Release 已创建成功
- tag 指向正确 commit
- Release 标题、正文、版本号一致
- 验证命令与本次实际执行结果一致

## Guardrails

- 不要复用已有 tag
- 不要 force push
- 不要把不属于本次 release 的脏改动一起提交
- 不要跳过验证
- 不要让 release notes 变成开发日志堆砌
- 不要伪造“已验证”的命令结果
