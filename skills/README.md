# Skills Directory

这个目录用于收纳 **MAARS 项目内的流程型说明、仓库定制 skill、以及后续 CLI / 发布 / 运维相关的项目知识**。

目录约定：

- 一个主题一个子目录，例如 `release/`、`maars-cli/`
- 每个主题目录的主入口文件固定为 `SKILL.md`
- 如果主题需要补充材料，可继续使用这些子目录：
  - `agents/`: 面向 agent 的元数据或提示词入口
  - `references/`: 模板、规范、样例
  - `examples/`: 实例命令或输出样例

当前已提供：

- `release/`: GitHub Release 发版流程、验证要求、双语 release notes 模板

建议新增主题时遵守：

- 只写 MAARS 相关的仓库事实和流程，不复制通用文档
- 优先记录“怎么做”和“为什么这么做”
- 如果流程依赖项目现状，明确写出涉及的文件、命令和 guardrails
