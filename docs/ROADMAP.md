# MAARS Roadmap

改进建议与开发路线图。按优先级排序，逐步推进。

已完成事项已归档到 [archive/roadmap-completed.md](archive/roadmap-completed.md)。

---

## P2 — 功能增强

### 7. 结构化日志 + LLM 成本追踪

**现状**: `log.jsonl` 已实现事件持久化和 token 回放。剩余：
- 每次 LLM 调用的 token 明细记录到 `meta.json`
- 按模型估算成本
- `GET /api/pipeline/stats` 接口

**决定**: 暂不推进，当前 log.jsonl + token 回放已满足需求。

---

## P3 — 长期方向

### 9. 论文输出质量提升

- 支持 LaTeX 输出格式
- 自动嵌入 artifacts 图表
- 参考文献管理（arXiv → BibTeX）
- 论文质量评分指标

---

### 10. 多 Session 并发

将 orchestrator 改为 session 级别实例管理，支持同时运行多个 pipeline。需要重构 SSE 订阅模型和 Docker 资源分配。

---

### 11. 开发体验改进

- 迁移到 `pyproject.toml`
- 添加 `ruff` 配置文件
- 添加 `pre-commit` hooks

---

## 优先级总览

| 优先级 | 编号 | 任务 | 复杂度 | 状态 |
|--------|------|------|--------|------|
| P2 | 7 | 结构化日志 + LLM 成本追踪 | 中 | Deferred |
| P3 | 9 | 论文输出质量提升 | 大 | |
| P3 | 10 | 多 Session 并发 | 大 | |
| P3 | 11 | 开发体验改进 | 中 | Partial |
