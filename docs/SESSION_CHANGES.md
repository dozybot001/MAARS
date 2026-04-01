# Session Changes — 代码简化与稳健性改进

> 基于 v11.0.0 (`5b63d90`) 的一系列改动。
> 目标：本地跑通、减少 bug、逻辑直接不绕弯子。

---

## 一、LLM 提供商简化（只保留 Google）

### backend/config.py
- 删除 `model_provider`, `anthropic_api_key`, `anthropic_model`, `openai_api_key`, `openai_model` 字段
- 删除 `active_api_key` / `active_model` 属性
- 删除 Anthropic/OpenAI 的 `os.environ.setdefault` 行
- 只保留 `google_api_key` 和 `google_model`
- 新增 `api_concurrency: int` 字段（控制 LLM 并发数）
- 所有字段**无默认值**（从 .env 读取，缺少则启动报错）
- 添加 `extra = "ignore"` 到 Config class（忽略 .env 中多余字段）
- 删除 `docker_sandbox_concurrency` 字段（已不在 config 中）

### backend/agno/models.py
- 简化为只创建 `Gemini` 模型
- 函数签名改为 `create_model(provider, model_id, api_key)` 但只支持 google
- 不再有 provider switch（无 Anthropic/OpenAI 分支）

### backend/agno/__init__.py
- `create_agno_stages` 删除 `model_provider` 参数
- 调用 `create_model("google", model_id, api_key)`
- 删除 `AgnoClient` 相关导入
- Research stage 直接传 `model` + `tools`，不再用 `AgnoClient`

### backend/main.py
- `create_agno_stages` 调用改为传 `settings.google_model` / `settings.google_api_key`
- 删除 `model_provider`/`active_model`/`active_api_key` 引用

---

## 二、删除 AgnoClient 包装层

### 删除文件：backend/agno/client.py
- 整个文件删除（148 行）
- `StreamEvent` dataclass 和 `AgnoClient` 类全部移除

### backend/pipeline/stage.py — `_stream_llm` 直接调用 Agno Agent
- 不再接收 `AgnoClient`，直接接收 `model` + `tools`
- 内部创建 `Agent(model=model, instructions=instruction, tools=tools, markdown=True)`
- 直接遍历 `agent.arun()` 的事件，映射 `RunEvent` 到 SSE chunk
- 事件处理：run_content, reasoning_step, tool_call_started, tool_call_completed, run_error, run_completed

### backend/pipeline/research.py
- `ResearchStage.__init__` 改为接收 `model` + `tools` 而非 `llm_client`
- 新增 `_llm()` 快捷方法调用 `_stream_llm`
- 新增 `_describe_capabilities()` 方法（原在 AgnoClient 中）

---

## 三、合并 Stage + AgentStage 为单个 Stage

### backend/pipeline/stage.py
- 删除 `AgentStage` 子类
- 所有功能合并到 `Stage` 基类
- 删除 `_run_id` 和 `_is_stale()` 机制
- 新增 `_stop_requested` 标志 + `request_stop()` 方法
- **模板方法模式**：`run()` 统一管 state 转换 + 异常处理，子类只实现 `_execute()`
  ```python
  async def run(self):
      self.state = RUNNING → emit
      try:
          self.output = await self._execute()
          self.state = COMPLETED → emit
      except CancelledError:
          return  # orchestrator 设 PAUSED
      except Exception:
          self.state = FAILED → emit error → raise
  ```
- `_stream_llm` 签名改为直接接收 `instruction: str, user_text: str`（不再接收 messages list）
- 全局 API 并发信号量：`_get_api_semaphore()` 基于 `settings.api_concurrency`
- `_stream_llm` 通过 `_stream_llm_inner` 包裹信号量
- 删除 `_extract_prompt()` 静态方法

---

## 四、SSE 广播简化

### backend/pipeline/orchestrator.py
- 删除 per-connection 订阅机制（`_subscribers` list, `subscribe()`, `unsubscribe()`）
- 改为单个全局 `event_queue: asyncio.Queue`
- `_broadcast()` 直接 `put_nowait` 到队列 + 追加写入 `events.jsonl`

### backend/routes/events.py
- 不再调用 `subscribe()`/`unsubscribe()`
- 直接从 `orchestrator.event_queue` 读取事件

---

## 五、四个全局操作集中到 orchestrator

### backend/pipeline/orchestrator.py — 完全重写
- **start()**: cancel 旧任务 → 检测 Kaggle → 创建 session → create_task
- **stop()**: 自动找 running stage → emit pausing → request_stop → kill_containers → cancel(5s timeout) → set PAUSED
- **resume()**: 自动找 paused stage → 清 stop 标志 → create_task 继续
- **shutdown()**: kill_containers + cancel_pipeline(5s timeout)
- 用 `_pipeline_task` 单个变量代替 `_tasks` dict
- `_cancel_pipeline(timeout)` 统一取消逻辑
- `_find_running_stage()` / `_find_paused_stage()` 辅助方法
- Kaggle 下载用 `asyncio.to_thread` 包装

### backend/routes/pipeline.py
- stop/resume 路由从 `/api/stage/{name}/stop` 改为 `/api/pipeline/stop`
- 不再需要前端传 stage name
- Docker status 路由的 `client.ping()` 用 `asyncio.to_thread` 包装

### backend/main.py — lifespan
- shutdown 逻辑简化为 `await orch.shutdown()`

### frontend/js/api.js
- `stageAction(stageName, action)` → `pipelineAction(action)`
- 调用路径改为 `/api/pipeline/stop` 和 `/api/pipeline/resume`

### frontend/js/pipeline-ui.js
- 导入改为 `pipelineAction`
- `handlePause` / `handleResume` 不再传 stage name

---

## 六、redecompose 改用 if/else 控制流

### backend/pipeline/research.py
- 删除 `_RedecomposeNeeded` 异常类
- `_execute_task_inner` 返回元组 `(needs_redecompose, task, result, review)`
- `_execute_all_tasks` 中用 `if needs_redecompose:` 代替 `isinstance(result, _RedecomposeNeeded)`
- `_redecompose_task` 签名改为直接接收 `task, result, review` 参数

---

## 七、去掉 contextvars

### backend/pipeline/research.py
- 删除 `import contextvars` 和 `_current_task_id: contextvars.ContextVar`
- 改为实例变量 `self._current_task_id: str | None`
- `_execute_task` 中直接设置 `self._current_task_id = task_id`

---

## 八、db.py 简化

### backend/db.py
- 提取顶层工具函数：`_read(path)`, `_read_json(path, default)`, `_write_json(path, data)`
- 所有读取方法统一用 `_read()` / `_read_json()`，不再逐个写 `path.exists()` 检查
- `_slugify` 从方法改为内联（在 `create_session` 中）
- 删除 `_meta_path()` / `_load_meta()` / `_save_meta()` 独立方法，用 `_read_json` / `_write_json` 代替
- 新增 `get_events_path()` 返回 `events.jsonl` 路径
- `execution_log` 改为 `append_execution_log()` 方法（在另一个 session 中改的）

---

## 九、docker_exec.py 简化

### backend/agno/tools/docker_exec.py
- 删除 `threading.Lock` (`_docker_lock`) 和 `threading.Semaphore` (`_container_semaphore`)
- 保留 `_containers_lock` 用于 `_active_containers` 的线程安全操作
- 删除全局 `_docker_client` 缓存和重连重试逻辑
- `_get_docker_client()` 简化为直接 `docker.from_env()`
- 提取 `_run_container()` 为独立函数，包含阻塞的 Docker 调用
- `code_execute` 改为 `async`，用 `asyncio.to_thread(_run_container, ...)` 避免阻塞 event loop
- `kill_all_containers()` 使用 `_containers_lock` 保护

---

## 十、team/stage.py 简化

### backend/team/stage.py
- 删除独立的 `_handle_event()` 方法（113 行），事件处理内联到 `_execute()` 中
- 删除 `state` dict 模式，用局部变量 `output_content` / `current_member`
- `run()` → `_execute()`（使用基类模板方法）
- 删除重复的 try/except state 管理（由基类 `run()` 统一处理）

### backend/team/refine.py + write.py
- `max_iterations` 从 10 降到 3

---

## 十一、prompts 收拢

### backend/pipeline/prompts.py
- 从 decompose.py 移入 `DECOMPOSE_SYSTEM_TEMPLATE`
- 新增 `build_decompose_system(atomic_definition, strategy)` 函数
- 新增 `build_decompose_user(task_id, description, context)` 函数
- 所有 `build_*_prompt` 函数返回 `(instruction, user_text)` 元组，不再返回 `list[dict]`

### backend/pipeline/decompose.py
- 删除内联的 `_SYSTEM_PROMPT_TEMPLATE` 和 `_build_user_prompt`
- 从 `prompts.py` 导入 `build_decompose_system`, `build_decompose_user`

---

## 十二、_extract_prompt 适配层去除

### backend/pipeline/stage.py
- `_stream_llm` 签名从 `messages: list[dict]` 改为 `instruction: str, user_text: str`
- 删除 `_extract_prompt()` 静态方法

### backend/pipeline/research.py
- `_llm()` 快捷方法签名同步更改
- 所有调用点从构造 messages list 改为直接传 instruction + user_text
- `stream_fn` lambda 签名从 `(msgs, cid, cl)` 改为 `(inst, ut, cid, cl)`

---

## 十三、events.jsonl 落盘

### backend/pipeline/orchestrator.py — `_broadcast()`
- 每个事件追加写入 `{session}/events.jsonl`
- 格式：每行一个 JSON，带 `ts` 时间戳
- 不做回放（纯落盘）

### backend/db.py
- 新增 `get_events_path()` 方法

---

## 十四、异步阻塞修复

### 三处阻塞调用用 asyncio.to_thread 包装：
1. **orchestrator.py**: `self._start_kaggle()` → `await asyncio.to_thread(...)`
2. **research.py**: `_preflight_docker()` → `await asyncio.to_thread(...)`
3. **routes/pipeline.py**: docker status 的 `client.ping()` → `await asyncio.to_thread(...)`
4. **docker_exec.py**: `code_execute` 改为 async，`_run_container` 用 `asyncio.to_thread` 在线程中执行

---

## 十五、start.sh 简化

- 浏览器自动打开从 30 行检测逻辑缩减为 `open http://localhost:8000`
- venv 自动创建和使用
- .env 缺失时从 `.env.example` 复制
- 新增：对比 .env.example 和 .env，自动补全缺失的配置项
- API key 检查简化为只检查 `MAARS_GOOGLE_API_KEY`

---

## 十六、.env.example

- 所有默认值集中在 .env.example（config.py 无默认值）
- 删除 Anthropic/OpenAI 配置项
- 新增 `MAARS_API_CONCURRENCY=1`
- 删除 `MAARS_DOCKER_SANDBOX_CONCURRENCY`
- 模型默认值 `gemini-3-flash-preview`

---

## 十七、pause 不清屏修复

### backend/pipeline/research.py + backend/team/stage.py
- `CancelledError` handler 不再设 state=IDLE 或 emit state 事件
- 由 orchestrator 的 `stop()` 统一设 PAUSED
- 这修复了 pause 时前端收到 `idle` 事件导致日志清空的问题

---

## 十八、models.py（Pydantic）

### backend/models.py
- `StageStatus` 删除 `rounds` 字段（`AgentStage` 已不存在）

---

## 文件清单

### 删除的文件
- `backend/agno/client.py`

### 新增的文件
- 无（events.jsonl 运行时生成）

### 修改的文件
- `backend/config.py`
- `backend/main.py`
- `backend/models.py`
- `backend/db.py`
- `backend/agno/__init__.py`
- `backend/agno/models.py`
- `backend/agno/tools/docker_exec.py`
- `backend/pipeline/orchestrator.py`
- `backend/pipeline/stage.py`
- `backend/pipeline/research.py`
- `backend/pipeline/decompose.py`
- `backend/pipeline/prompts.py`
- `backend/routes/pipeline.py`
- `backend/routes/events.py`
- `backend/team/stage.py`
- `backend/team/refine.py`
- `backend/team/write.py`
- `frontend/js/api.js`
- `frontend/js/pipeline-ui.js`
- `start.sh`
- `.env`
- `.env.example`
