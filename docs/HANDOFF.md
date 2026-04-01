# 交付日志：v12.0.0 SSE 架构重构

## 当前状态

`main` 分支现在是 v12.0.0（commit a8e152a 基础上 + start.sh 修复）。
基于 v11.0.0 重写，**覆盖了远端之前的 23 个 commit**。

## 被覆盖的改动

远端之前有 23 个 commit 已保存到 `archive/vue-migration` 分支，包含：

1. **Vue 3 前端迁移** — `frontend/src/` 下的 Vue 组件（App.vue, LogViewer.vue 等）
2. **多 Provider 配置** — anthropic/openai 支持、per-stage model override
3. **Session 管理** — `backend/routes/sessions.py`、DB 的 session 列表/恢复
4. **安全加固** — AccessTokenMiddleware、pip requirements 校验、Docker 输入清洗
5. **测试** — `tests/` 目录下 90+ 单元测试
6. **CI** — GitHub Actions workflow（已被删除）
7. **start.sh 增强** — 完整 checklist 版本（start-ref.sh 风格）
8. **文档** — ROADMAP.md、前端迁移计划

## 需要恢复的改动

以下改动被 v12.0.0 覆盖，需要从 `archive/vue-migration` 分支恢复并适配新架构：

### 必须恢复
- `tests/` — 所有测试文件（需适配新 API：`_send` 替代 `_emit`，新 DB 方法等）
- `backend/routes/sessions.py` — session 列表/恢复 API
- `backend/db.py` 中的 session 管理方法 — `list_sessions()`, `load_session()` 等
- 安全相关 — `AccessTokenMiddleware`、`sanitize_requirements()`、`validate_language()`
- `.gitattributes` — LF 行尾强制

### 可选恢复
- Vue 3 前端 — `frontend/src/` 完整 Vue 迁移（但需要适配新 SSE 架构）
- 多 Provider 配置 — anthropic/openai 支持（当前设计故意只保留 Google）
- `docs/ROADMAP.md` — 路线图

## v12.0.0 的关键架构变更

恢复改动时需要注意以下 breaking changes：

### 后端
- `Stage._emit()` 已删除 → 替换为 `Stage._send(chunk?, **extra)`
- `Stage.__init__` 不再接受 `**kwargs`
- `ResearchStage.__init__` 签名：`(name, model, tools, max_iterations, db)`
- `db.execution_log` 内存列表已删除 → 改用 `db.append_execution_log()` 写文件
- `db.get_plan_list()` 返回 `list[dict]`（不再是 raw JSON string）
- `db.get_plan_tree()` 返回 `dict`（不再是 raw JSON string）
- `db.get_events_path()` 已删除（events.jsonl 不再使用）
- `docker_sandbox_concurrency` 配置已删除（统一用 `api_concurrency`）
- `config.py` 使用 `extra = "ignore"` 忽略未知 env 变量
- `orchestrator._broadcast()` 不再写 events.jsonl，只推 queue

### SSE 架构
- 统一事件格式：`{stage, phase?, chunk?, status?, task_id?, error?}`
- 有 chunk = 进行中，无 chunk = 结束信号（先写 DB 再发）
- `events.py` SSE endpoint 使用默认 `message` 类型，不再用 `event: type`
- 详见 `docs/SSE_REFACTOR.md`

### 前端
- 所有 SSE 事件通过 `source.onmessage` 接收，emit 到统一的 `'sse'` 总线
- pipeline-ui 由首次出现的 stage/phase 驱动，不调 API
- log-viewer section 由 chunk 按需创建，不依赖 state 事件
- process-viewer 在 done signal 时 fetch DB 渲染

## 恢复步骤建议

```bash
# 1. 查看 archive 分支的改动
git diff main..archive/vue-migration -- tests/
git diff main..archive/vue-migration -- backend/routes/sessions.py
git diff main..archive/vue-migration -- backend/db.py

# 2. Cherry-pick 或手动合并需要的文件
# 注意：直接 cherry-pick 会冲突，建议手动读取并适配

# 3. 适配新架构后运行测试
source .venv/bin/activate
python -m pytest tests/ -v
```
