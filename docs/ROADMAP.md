# MAARS Roadmap

改进建议与开发路线图。按优先级排序，逐步推进。

---

## P0 — 安全与基础质量

### 1. 修复 `requirements` 命令注入风险

**位置**: `backend/agno/tools/docker_exec.py:93`

**问题**: `requirements` 参数直接拼接到 shell 命令中：

```python
cmd_parts.append(f"pip install --quiet {requirements}")
```

恶意 LLM 输出可能注入任意 shell 命令。虽然在容器内执行，但挂载的 artifact volume 是 `rw`，数据仍有被破坏的风险。

**方案**: 对 `requirements` 做白名单校验（只允许 `[a-zA-Z0-9._-]` 字符的包名+版本号），拒绝含 `;`、`&&`、`|`、`$` 等 shell 元字符的输入。

---

### 2. 核心模块单元测试 + CI

**问题**: 项目没有任何测试。DAG 调度、checkpoint/resume、redecompose 等核心逻辑缺少回归保护。

**方案**:

- 添加 `pytest` 配置（`pyproject.toml` 或 `pytest.ini`）
- 优先覆盖以下模块：
  - `topological_batches()` — DAG 排序正确性、环检测、空输入
  - `decompose()` — mock LLM，验证递归拆分和 ID 编号
  - `_parse_verification()` — 各种 JSON 格式和 fallback
  - `ResearchDB` — session 创建、读写一致性、promote_best_score 逻辑
  - `_check_score_improved()` — minimize/maximize、plateau 检测
- 添加 `.github/workflows/ci.yml`，在 PR 时自动运行测试 + lint

---

## P1 — 健壮性

### 3. Docker 执行改为真正的异步

**位置**: `backend/agno/tools/docker_exec.py`

**问题**: 使用 `threading.Semaphore` 和同步 Docker SDK 调用，但调用方是 `asyncio` 协程。`_container_semaphore.acquire()` 会阻塞事件循环，影响 SSE 推送和其他并发任务。

**方案**: 将 `code_execute` 内部的 Docker 操作包装到 `asyncio.to_thread()` 中执行，或使用 `aiodocker` 异步客户端。信号量改为 `asyncio.Semaphore`。

---

### 4. 文件 DB 并发保护

**位置**: `backend/db.py`

**问题**: `ResearchDB` 的所有读写操作都是裸 `Path.write_text()` / `Path.read_text()`。并行执行的任务可能同时写入 `plan_list.json`、`best_score.json` 等共享文件，造成数据竞争或文件损坏。

**方案**: 对共享文件（`plan_list.json`、`plan_tree.json`、`best_score.json`、`latest_score.json`、`meta.json`）的读写操作加锁。可选方案：

- `asyncio.Lock`（适合纯异步路径）
- `filelock` 库（适合跨进程场景）
- 先写临时文件再原子 rename（防止写入中断导致文件损坏）

---

### 5. Session 历史管理 API

**问题**: 没有 API 可以列出、查看或删除历史 session。用户只能手动浏览 `results/` 目录。

**方案**:

- `GET /api/sessions` — 列出所有 session（ID、创建时间、状态、idea 摘要）
- `GET /api/sessions/{id}` — 查看特定 session 的完整状态和输出文件
- `DELETE /api/sessions/{id}` — 删除 session 及其所有文件
- 前端添加 session 侧边栏或历史记录面板

---

## P2 — 功能增强

### 6. Per-stage 模型配置

**问题**: 所有阶段共用同一个 `MAARS_MODEL_PROVIDER` + `MAARS_{PROVIDER}_MODEL`。实际上不同阶段有不同需求：

- **Refine**: 需要创造力和广度（适合高能力模型）
- **Research**: 需要精确推理和工具使用（适合推理模型）
- **Write**: 需要长文本生成质量（适合写作能力强的模型）

**方案**: 支持 per-stage 配置覆盖：

```env
MAARS_REFINE_PROVIDER=anthropic
MAARS_REFINE_MODEL=claude-opus-4-6
MAARS_RESEARCH_PROVIDER=google
MAARS_RESEARCH_MODEL=gemini-2.5-pro
MAARS_WRITE_PROVIDER=anthropic
MAARS_WRITE_MODEL=claude-sonnet-4-6
```

未配置则 fallback 到全局 `MAARS_MODEL_PROVIDER` / `MAARS_{PROVIDER}_MODEL`。

---

### 7. 结构化日志 + LLM 成本追踪

**问题**: 当前只有 SSE 事件流用于前端展示，没有持久化日志。pipeline 失败后难以排查；LLM 调用的 token 使用量和成本没有统计。

**方案**:

- 集成 Python `logging` 模块，关键事件（阶段转换、LLM 调用、Docker 执行、错误）写入 `results/{id}/run.log`
- 在 `AgnoClient` 层记录每次 LLM 调用的 input/output token 数量
- 在 `meta.json` 中累计 token 使用量和估算成本
- 添加 `GET /api/pipeline/stats` 返回当前 session 的 token/成本统计

---

### 8. API 认证

**问题**: 所有 `/api/*` 路由完全开放。绑定 `0.0.0.0:8000` 意味着局域网内任何人都能启动 pipeline。

**方案**: 添加一个可选的 `MAARS_API_KEY` 环境变量。设置后，所有请求需在 `Authorization: Bearer <key>` 头中携带。未设置则保持当前开放行为（本地开发友好）。

---

## P3 — 长期方向

### 9. 论文输出质量提升

- 支持 LaTeX 输出格式（面向学术投稿场景）
- 自动嵌入 artifacts 中的图表到论文中（当前需 agent 手动引用路径）
- 参考文献管理：从 arXiv 搜索结果自动生成 BibTeX
- 论文质量评分指标（结构完整性、引用覆盖、实验充分性）

---

### 10. 多 Session 并发

**问题**: `PipelineOrchestrator` 是全局单例，一次只能运行一个 pipeline。

**方案**: 将 orchestrator 改为 session 级别的实例管理，通过 session ID 路由请求。需要重构 SSE 订阅模型和 Docker 资源分配。

---

### 11. 开发体验改进

- 迁移到 `pyproject.toml`（现代 Python 项目标准）
- 添加 `ruff` 配置（linting + formatting）
- 添加 `pre-commit` hooks
- 前端如需大幅扩展，考虑引入轻量框架（Svelte / Vue）

---

## 优先级总览

| 优先级 | 编号 | 任务 | 复杂度 | 状态 |
|--------|------|------|--------|------|
| P0 | 1 | 修复 requirements 命令注入 | 小 | Done |
| P0 | 2 | 核心模块单元测试 + CI | 中 | Done |
| P1 | 3 | Docker 执行改为异步 | 小 | Done |
| P1 | 4 | 文件 DB 并发保护 | 小 | Done |
| P1 | 5 | Session 历史管理 API | 中 | |
| P2 | 6 | Per-stage 模型配置 | 小 | |
| P2 | 7 | 结构化日志 + LLM 成本追踪 | 中 | |
| P2 | 8 | API 认证 | 小 | |
| P3 | 9 | 论文输出质量提升 | 大 | |
| P3 | 10 | 多 Session 并发 | 大 | |
| P3 | 11 | 开发体验改进 | 中 | |
