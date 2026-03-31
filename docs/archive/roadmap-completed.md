# MAARS Roadmap Completed

已完成路线图事项归档。

---

## P0 — 安全与基础质量

### 1. 修复 `requirements` 命令注入风险

- 对 `requirements` 做白名单校验，拒绝含 shell 元字符的输入。

### 1b. 修复 `language` 命令注入风险

- 对 `language` 做白名单校验，仅允许受支持解释器。

### 2. 核心模块单元测试 + CI

- 建立 `pytest` 测试基线。
- 接入 GitHub Actions CI。

### 2b. DAG 调度器 fail fast

- `topological_batches` 遇到环或缺失依赖时直接 `raise ValueError`。

---

## P1 — 健壮性

### 3. Docker 执行改为真正的异步

- Docker 阻塞操作包装到 `asyncio.to_thread()`。
- 并发控制切换到 `asyncio.Semaphore`。

### 4. 文件 DB 并发保护

- 共享文件读写加 `threading.Lock`。
- 文件写入统一走原子 rename。

### 5. Session 历史管理 API

- `GET /api/sessions`
- `GET /api/sessions/{id}`
- `GET /api/sessions/{id}/state`
- `DELETE /api/sessions/{id}`
- 前端左侧边栏 session 卡片集成 Start/Pause/Resume

### 5b. Session 前端状态完整恢复

- 后端 `get_session_state()` 从现有文件推导状态。
- `log.jsonl` 支持 reasoning log 回放。
- 前端 `loadSessionState()` 通过事件回放重建 UI。
- token 计数可从 log 恢复。
- session snapshot 可区分 `paused/completed` 与部分执行状态。

### 5c. 页面刷新自动暂停 + 断点续传

- `beforeunload` 自动触发 `POST /api/pipeline/stop`。
- Pause 与 beforeunload 统一走同一中断入口。
- `resume_stage` 利用 DB 产物推断恢复起点。
- `syncFromStatus` 改为无副作用同步。

---

## P2 — 功能增强

### 6. Per-stage 模型配置

- 支持 `MAARS_{STAGE}_PROVIDER` / `MAARS_{STAGE}_MODEL` 覆盖全局配置。

### 8. API 认证

- 支持可选 `MAARS_API_KEY`。
- `/api/*` 路由支持 `Authorization: Bearer <key>`。
- SSE 与 stop 请求已通过 header 认证。
- 未设置 API key 启动时打印 warning。

---

## P3 — 开发体验改进（已完成部分）

- 前端迁移到 Vue 3 + Pinia + Vite
- Pydantic `ConfigDict` 迁移
- 删除 frontend 源码目录 fallback
- CI 覆盖前端构建：`npm ci && npm run build`
- README 更新，反映 Vue 3、Write 阶段重构与安全改进
