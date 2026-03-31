# MAARS Roadmap

改进建议与开发路线图。按优先级排序，逐步推进。

---

## P0 — 安全与基础质量

### 1. 修复 `requirements` 命令注入风险

**位置**: `backend/agno/tools/docker_exec.py`

**问题**: `requirements` 参数直接拼接到 shell 命令中，恶意 LLM 输出可能注入任意 shell 命令。

**方案**: 对 `requirements` 做白名单校验，拒绝含 shell 元字符的输入。

### 1b. 修复 `language` 命令注入风险

**问题**: `language` 参数直接拼入 `bash -c` 命令，未做任何校验。由于容器默认开启网络，可外传数据。

**方案**: 白名单校验 `{"python", "Rscript"}`，非法值直接拒绝。

---

### 2. 核心模块单元测试 + CI

**方案**: `pytest` + GitHub Actions CI，覆盖 DAG 调度、DB 读写、分数逻辑、输入校验等。

### 2b. DAG 调度器 fail fast

**问题**: `topological_batches` 遇到环或悬空依赖时静默降级，把剩余任务强行塞进一个 batch。

**方案**: 检测到环或缺失依赖时 `raise ValueError`，明确暴露非法计划。

---

## P1 — 健壮性

### 3. Docker 执行改为真正的异步

将 Docker 操作包装到 `asyncio.to_thread()`，信号量改为 `asyncio.Semaphore`。

---

### 4. 文件 DB 并发保护

共享文件读写加 `threading.Lock` + 原子 rename 写入。

---

### 5. Session 历史管理 API

- `GET /api/sessions` — 列出所有 session
- `GET /api/sessions/{id}` — 查看详情
- `GET /api/sessions/{id}/state` — 完整前端可恢复状态（从 DB 文件推导）
- `DELETE /api/sessions/{id}` — 删除 session
- 前端左侧边栏（汉堡按钮触发），session 卡片集成 Start/Pause/Resume

### 5b. Session 前端状态完整恢复

**问题**: 切换到历史 session 时，前端需要重建完整 UI 状态。

**方案**:
- 后端 `get_session_state()` 从现有文件推导所有状态（stage/node states、documents、decomp tree、exec batches、task states、scores），零额外持久化
- `log.jsonl`：broadcast 事件追加写入，支持左面板 reasoning log 回放
- 前端 `loadSessionState()` 按正常事件流顺序回放：设 store 值 + `nextTick` 让 watcher 自然触发 DOM 操作，ProcessViewer/LogViewer 零改动
- Token 计数从 log 中的 tokens 事件累加恢复
- Session snapshot 精确推断：research 区分 paused/completed，execute 区分部分完成/全部完成

### 5c. 页面刷新自动暂停 + 断点续传

**问题**: 页面意外刷新时运行中的 session 会失控。

**方案**:
- `beforeunload` + `fetch(..., { keepalive: true })` 发 `POST /api/pipeline/stop`（附 Authorization header）
- 统一中断入口：侧边栏 Pause 和 beforeunload 都走 `/api/pipeline/stop`
- `resume_stage` 利用 DB 产物推断起点：refine 有产物则跳到 research，research 内部各 phase 自行跳过已完成步骤
- `syncFromStatus` 直接设值，不经过 `handleStageState`，避免 idle stage 触发 reset

---

## P2 — 功能增强

### 6. Per-stage 模型配置

支持 `MAARS_{STAGE}_PROVIDER` / `MAARS_{STAGE}_MODEL` 环境变量覆盖，未配置则 fallback 到全局。

---

### 7. 结构化日志 + LLM 成本追踪

**现状**: `log.jsonl` 已实现事件持久化和 token 回放。剩余：
- 每次 LLM 调用的 token 明细记录到 `meta.json`
- 按模型估算成本
- `GET /api/pipeline/stats` 接口

**决定**: 暂不推进，当前 log.jsonl + token 回放已满足需求。

---

### 8. API 认证

可选 `MAARS_API_KEY`，设置后 `/api/*` 路由需 `Authorization: Bearer <key>` header。SSE 和 stop 请求均通过 header 认证，不再接受 query param。未设置 API key 启动时打印 WARNING。

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

- ~~迁移到 `pyproject.toml`~~
- ~~添加 `ruff` 配置~~
- ~~添加 `pre-commit` hooks~~
- ~~前端引入轻量框架~~ → 已迁移到 Vue 3 + Pinia + Vite
- Pydantic `ConfigDict` 迁移（已完成）
- 删除 frontend 源码目录 fallback（已完成）
- CI 覆盖前端构建：`npm ci && npm run build`（已完成）
- README 更新（已完成：反映 Vue 3 + Write 阶段重构 + 安全改进）

---

## 优先级总览

| 优先级 | 编号 | 任务 | 复杂度 | 状态 |
|--------|------|------|--------|------|
| P0 | 1 | 修复 requirements 命令注入 | 小 | Done |
| P0 | 1b | 修复 language 命令注入 | 小 | Done |
| P0 | 2 | 核心模块单元测试 + CI | 中 | Done |
| P0 | 2b | DAG 调度器 fail fast | 小 | Done |
| P1 | 3 | Docker 执行改为异步 | 小 | Done |
| P1 | 4 | 文件 DB 并发保护 | 小 | Done |
| P1 | 5 | Session 历史管理 API | 中 | Done |
| P1 | 5b | Session 前端状态完整恢复 | 大 | Done |
| P1 | 5c | 页面刷新自动暂停 + 断点续传 | 中 | Done |
| P2 | 6 | Per-stage 模型配置 | 小 | Done |
| P2 | 7 | 结构化日志 + LLM 成本追踪 | 中 | Deferred |
| P2 | 8 | API 认证 | 小 | Done |
| P3 | 9 | 论文输出质量提升 | 大 | |
| P3 | 10 | 多 Session 并发 | 大 | |
| P3 | 11 | 开发体验改进 | 中 | Partial |
