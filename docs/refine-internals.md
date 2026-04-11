# Refine 阶段内部实现 · Walkthrough

> 面向开发者的实现级参考。目标是让新读者从零理解 `maars refine` 从命令行调用到 session 落盘的每一步。
>
> 代码位置用 `file_path:line_number` 标注，方便跳转。如果代码有显著变化，这份文档可能会滞后——以 git 的 `src/maars/` 为准。
>
> 相关文档：[`concept.md`](concept.md)（思想） / [`architecture.md`](architecture.md)（技术栈决策） / [`graph.md`](graph.md)（graph schema） / [`cli.md`](cli.md)（用户命令参考）。

## 目录

1. [分层总览](#1-分层总览)
2. [一次完整 refine run 的时间线](#2-一次完整-refine-run-的时间线)
3. [Node 函数内部发生什么](#3-node-函数内部发生什么)
4. [条件边](#4-条件边)
5. [State 类型](#5-state-类型)
6. [Checkpointer 和 Session 落盘](#6-checkpointer-和-session-落盘)
7. [关键设计决策](#7-关键设计决策)
8. [Gotchas](#8-几个值得注意的-gotcha)
9. [文件清单](#9-文件清单实际代码量)

---

## 1. 分层总览

```
┌──────────────────────────────────────────────────────────────┐
│ CLI 层 (typer command)                                       │
│   cli.py:refine() → asyncio.run(_refine_async())             │
├──────────────────────────────────────────────────────────────┤
│ Session 管理层                                               │
│   _next_thread_id, _session_dir_for, _save_refine_session    │
│   _esc_listener_supported, _listen_for_esc                   │
│   _extract_usage_metadata, _accumulate_usage                 │
├──────────────────────────────────────────────────────────────┤
│ Graph 编排层 (LangGraph)                                     │
│   graphs/refine.py:build_refine_graph(checkpointer)          │
│   ├── explorer_node(state) → dict                            │
│   ├── critic_node(state) → dict                              │
│   └── should_continue(state) → "explorer" | END              │
├──────────────────────────────────────────────────────────────┤
│ Agent 层 (纯 LLM call 封装)                                  │
│   agents/explorer.py:draft_proposal(...) → str               │
│   agents/critic.py:critique_draft(...) → CritiqueFeedback    │
├──────────────────────────────────────────────────────────────┤
│ Model 层                                                     │
│   models.py:get_chat_model()  → ChatGoogleGenerativeAI       │
│   models.py:get_search_model() → model.bind_tools([google])  │
├──────────────────────────────────────────────────────────────┤
│ Prompt 层                                                    │
│   prompts/explorer.py:EXPLORER_SYSTEM_PROMPT                 │
│   prompts/critic.py:CRITIC_SYSTEM_PROMPT                     │
├──────────────────────────────────────────────────────────────┤
│ State 层 (TypedDict schemas)                                 │
│   state.py:RefineState (TypedDict + reducer)                 │
│   state.py:Issue (Pydantic BaseModel)                        │
│   agents/critic.py:CritiqueFeedback (Pydantic for LLM out)   │
├──────────────────────────────────────────────────────────────┤
│ Persistence                                                  │
│   AsyncSqliteSaver → data/checkpoints.db (LangGraph state)   │
│   _save_refine_session → data/refine/{NNN}/ (user artifacts) │
└──────────────────────────────────────────────────────────────┘
```

**关键原则**：LangGraph 管 graph state + checkpoint；CLI 层管 UX（auto thread id、spinner、ESC、session dir、usage tracking）；Agent 层是无状态的纯函数调用；Model 层只负责构造 `ChatGoogleGenerativeAI` 实例。

---

## 2. 一次完整 refine run 的时间线

以 `uv run maars refine "研究大模型推理"` 为例，从用户按 Enter 到 session 保存落盘。

### 2.1 CLI 入口解析（同步）

**`cli.py:refine()`**：

```python
@app.command()
def refine(
    raw_idea: str = typer.Argument("", ...),
    thread_id: str = typer.Option(None, "--thread", ...),
    from_file: Path = typer.Option(None, "--from-file", "-f", ...),
) -> None:
```

- typer 解析 args → `raw_idea="研究大模型推理"`，`thread_id=None`，`from_file=None`
- 如果 `from_file is not None`：读文件内容覆盖 `raw_idea`
- 校验 `raw_idea.strip()` 非空，否则 exit 1
- `thread_id is None` → 调 **`cli.py:_next_thread_id()`**

### 2.2 Thread ID 自动分配

**`cli.py:_next_thread_id()`**：

```python
def _next_thread_id() -> str:
    refine_dir = DATA_DIR / "refine"
    refine_dir.mkdir(parents=True, exist_ok=True)
    existing_nums = [int(p.name) for p in refine_dir.iterdir()
                     if p.is_dir() and p.name.isdigit()]
    next_num = max(existing_nums, default=0) + 1
    return f"refine-{next_num:03d}"
```

- 扫描 `data/refine/` 所有纯数字目录名（过滤掉 `verify-stream` 这种非数字的自定义 id）
- 取最大值 + 1，补齐到 3 位：`"refine-001"` / `"refine-002"` / ...
- **只扫纯数字目录**的意思是：用户手动指定的 `--thread exp1` 不会占用编号序列

然后 `asyncio.run(_refine_async(raw_idea, thread_id))` 切换到 async 域。

### 2.3 `_refine_async` 初始化

**`cli.py:_refine_async()`**：

```python
async def _refine_async(raw_idea: str, thread_id: str) -> None:
    # ... imports ...
    console = Console()
    started_at = datetime.now(timezone.utc)
    usage_by_node: dict[str, dict[str, int]] = {
        "explorer": _empty_usage_bucket(),
        "critic": _empty_usage_bucket(),
    }
    serde = JsonPlusSerializer(
        allowed_msgpack_modules=[("maars.state", "Issue")]
    )
```

关键点：

- **`started_at`** 用于后续算 `duration_seconds`（存到 meta.json）
- **`usage_by_node`** 是一个 mutable accumulator，stream loop 里会边跑边累加 tokens
- **`serde`** 是 LangGraph 的 serializer，显式 allowlist `maars.state.Issue` 类型，否则 checkpointer 反序列化会报 security warning（LangGraph 1.x 新增的安全机制）

### 2.4 Checkpointer + Graph 构建

```python
async with AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB)) as checkpointer:
    checkpointer.serde = serde
    graph = build_refine_graph(checkpointer)
```

**`AsyncSqliteSaver.from_conn_string(path)`** 是 LangGraph 官方 API，返回一个 async context manager。在 context 内部，它管理 `aiosqlite` 连接。**两个常见坑**：

1. `from_conn_string(...)` **不接受** `serde=` kwarg，必须 post-assignment：`checkpointer.serde = serde`
2. 不能用同步 `SqliteSaver` 跟 `astream_events(v2)` 一起用——async stream 会 raise `NotImplementedError: aget_tuple not supported`

**`graphs/refine.py:build_refine_graph()`**：

```python
def build_refine_graph(checkpointer):
    workflow = StateGraph(RefineState)
    workflow.add_node("explorer", explorer_node)
    workflow.add_node("critic", critic_node)
    workflow.add_edge(START, "explorer")
    workflow.add_edge("explorer", "critic")
    workflow.add_conditional_edges("critic", should_continue)
    return workflow.compile(checkpointer=checkpointer)
```

graph 拓扑非常简单：

```
START → explorer → critic → should_continue(state)
                              ├── return "explorer" (loop back)
                              ├── return END (passed=True)
                              └── return END (round >= MAX_ROUND)
```

注意 `should_continue` 只关联到 `critic` 的 out 边（`add_conditional_edges("critic", ...)`），不是关联到 explorer。因为 explorer → critic 是无条件的。

### 2.5 检查现有 state + 准备 input

```python
config = {"configurable": {"thread_id": thread_id}}
existing = await graph.aget_state(config)
has_state = bool(existing and existing.values)

if has_state:
    # Resume mode
    input_state = None
else:
    # New run mode
    input_state = {"raw_idea": raw_idea, "round": 0}
```

LangGraph 的 resume 语义：

- 传 `input_state = None` + 已有的 `thread_id` → 从最后一个 checkpoint 继续，下一个要跑的 node 是 state 里 `next_nodes` 指示的节点
- 传完整 `input_state` dict + 新 `thread_id` → 从 `START` 开始新 run
- 传完整 dict + 已有 `thread_id` → 从 `START` 开始但会 merge 进现有 state（有坑，通常不这么用）

### 2.6 启动 ESC listener

```python
cancel_event = asyncio.Event()
esc_task = asyncio.create_task(_listen_for_esc(cancel_event))
interrupted = False
current_status = None
```

**`cli.py:_listen_for_esc(cancel_event)`** 是一个 async task：

```python
async def _listen_for_esc(cancel_event):
    if not _esc_listener_supported():
        await cancel_event.wait()  # park forever until cancelled
        return

    import termios, tty
    loop = asyncio.get_running_loop()
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    def _on_stdin():
        ch = sys.stdin.read(1)
        if ch == "\x1b":  # ESC
            cancel_event.set()

    try:
        tty.setcbreak(fd)                 # stdin → cbreak raw mode
        loop.add_reader(fd, _on_stdin)    # non-blocking fd reader
        await cancel_event.wait()         # sleep until ESC or caller cancel
    finally:
        loop.remove_reader(fd)
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)  # restore
```

**关键机制**：

1. **`tty.setcbreak(fd)`** 把 stdin 从 canonical 模式切到 cbreak 模式——canonical 下 ESC 会等 Enter 才传过来，cbreak 下每个字符立即可读
2. **`loop.add_reader(fd, callback)`** 把 fd 注册进 asyncio event loop 的 selector，当 fd 可读时 loop 调 `callback`——这是 **非阻塞** 的，不会阻塞主协程
3. **`cancel_event.wait()`** 让这个 task 挂起直到事件被设置（用户按 ESC 或主协程主动 set）
4. **`finally`** 保证无论什么情况终端都恢复到 canonical mode，不会让用户的 shell 乱

`_esc_listener_supported()` 是 `sys.platform != "win32" and sys.stdin.isatty()`——Windows 上 `termios` 不存在，pipe/subprocess 下 stdin 不是 TTY，两种情况都退化到"no-op listener + Ctrl-C fallback"。

### 2.7 Stream 主循环

```python
try:
    async for event in graph.astream_events(input_state, config=config, version="v2"):
        if cancel_event.is_set():
            interrupted = True
            break

        kind = event["event"]
        name = event.get("name", "")
        metadata = event.get("metadata", {}) or {}
        langgraph_node = metadata.get("langgraph_node", "")
        # ... dispatch ...
```

**`graph.astream_events(input_state, config, version="v2")`** 是一个 async iterator，每个 event 是一个 dict 带：

- `event`: event 类型字符串（`on_chain_start` / `on_chain_end` / `on_chat_model_start` / `on_chat_model_stream` / `on_chat_model_end` / `on_tool_start` / 等）
- `name`: 触发 event 的 runnable 名字（对 node 级 event 是 `"explorer"` / `"critic"`；对 LLM 级 event 是 `"ChatGoogleGenerativeAI"`）
- `metadata`: dict，**关键**的 `langgraph_node` key 告诉你当前这个 event 发生在哪个 node 的执行上下文里
- `data`: 具体数据（对 `on_chain_end`，`data.output` 是 node function 的 return；对 `on_chat_model_end`，`data.output` 是 `AIMessage`）
- `tags`, `run_id`, `parent_ids` 等元信息

**CLI 只消费三种 event**：

#### (a) Token usage 追踪 — `on_chat_model_end`

```python
if kind == "on_chat_model_end" and langgraph_node in ("explorer", "critic"):
    data = event.get("data", {}) or {}
    usage_meta = _extract_usage_metadata(data)
    _accumulate_usage(usage_by_node[langgraph_node], usage_meta)
```

**这里是关键**：通过 `metadata.langgraph_node` 区分当前 LLM 调用属于哪个 node，然后把 usage 归到对应 bucket。`_extract_usage_metadata` 是 defensive：

```python
def _extract_usage_metadata(data):
    output_obj = data.get("output")
    # 直接 AIMessage.usage_metadata
    usage = getattr(output_obj, "usage_metadata", None)
    if usage: return usage
    # ChatGeneration wrapper
    message = getattr(output_obj, "message", None)
    if message is not None:
        usage = getattr(message, "usage_metadata", None)
        if usage: return usage
    # dict fallback
    if isinstance(output_obj, dict):
        return output_obj.get("usage_metadata")
    return None
```

探测三种形状（`AIMessage` 直接、`ChatGeneration.message`、plain dict）——LangChain 1.x 的 `astream_events(v2)` 通常给 AIMessage，但不完全信任 forward compat。

#### (b) Node 开始 — `on_chain_start` (name in explorer/critic)

```python
if kind == "on_chain_start":
    if current_status is not None:
        current_status.stop()
    current_status = console.status(
        f"[cyan]→[/cyan] [bold]{name}[/bold] thinking...",
        spinner="dots",
    )
    current_status.start()
```

**`console.status()`** 返回一个 Rich `Status` 对象，底层是 `rich.live.Live` + `rich.spinner.Spinner`。`.start()` 激活一个独立的 refresh thread 定时重绘 spinner。**注意**：启动新 spinner 前先 stop 旧的，避免 orphan live instance 叠加在 terminal 上。

#### (c) Node 结束 — `on_chain_end` (name in explorer/critic)

```python
elif kind == "on_chain_end":
    if current_status is not None:
        current_status.stop()   # 先停 spinner,让 stdout 干净
        current_status = None
    # 然后打印永久 summary line
    data = event.get("data", {}) or {}
    output = data.get("output", {}) or {}
    # ... format "ok explorer round 1 — draft generated (N chars)" 或 critic summary ...
```

**关键顺序**：先停 spinner，再打印永久 summary，**不能颠倒**——`console.print` 在 Live 活跃时会被 live 覆盖。

---

## 3. Node 函数内部发生什么

### 3.1 Explorer — `graphs/refine.py:explorer_node`

```python
def explorer_node(state: RefineState) -> dict:
    draft = draft_proposal(
        raw_idea=state["raw_idea"],
        prior_draft=state.get("draft"),
        prior_issues=state.get("issues"),
    )
    return {"draft": draft, "round": state.get("round", 0) + 1}
```

**Thin wrapper**——从 state 读 3 个字段，调 agent 函数，返回要写回 state 的 partial dict（`draft` + 递增的 `round`）。不写 `raw_idea`（它是 immutable input），不写 `issues` / `resolved` / `passed`（那是 Critic 的职责）。

**`agents/explorer.py:draft_proposal()`**：

```python
def draft_proposal(raw_idea, *, prior_issues=None, prior_draft=None):
    model = get_search_model(temperature=0.2)

    if prior_draft and prior_issues:
        # Revision mode
        issues_block = "\n".join(
            f"- [{i.id}] ({i.severity}) {i.summary}: {i.detail}"
            for i in prior_issues
        )
        user_message = f"""## Raw idea
{raw_idea}
## Prior draft
{prior_draft}
## Critic 的 issues（请逐个解决）
{issues_block}
请修订 prior draft，针对性解决 issues，输出新的 draft。"""
    else:
        # First-round mode
        user_message = f"""## Raw idea
{raw_idea}
请根据这个想法起草一份研究提案。"""

    response = model.invoke([("system", EXPLORER_SYSTEM_PROMPT), ("human", user_message)])
    # ... content block extraction ...
    return text
```

**两点**：

1. **两种模式的 prompt 结构不同**：第一轮只有 raw_idea；后续轮次在 user message 里 **完整拼接** raw_idea + prior_draft + prior_issues（作为纯文本 context）。**没有 message history 累积**——每次 invoke 都是独立 `[system, human]` 两条 message。
2. **`get_search_model(temperature=0.2)`** 返回一个**已经 bind 了 google_search grounding tool 的 runnable**，不是裸 model。temperature=0.2 是为了 Explorer 有一定的创造性，但不要太发散。

### 3.2 Model 层 — `models.py`

```python
def get_chat_model(*, model=None, temperature=0.0):
    return ChatGoogleGenerativeAI(
        model=model or CHAT_MODEL,
        temperature=temperature,
    )

def get_search_model(*, model=None, temperature=0.0):
    return ChatGoogleGenerativeAI(
        model=model or CHAT_MODEL,
        temperature=temperature,
    ).bind_tools([{"google_search": {}}])
```

**`bind_tools([{"google_search": {}}])`** 是 Gemini 的 grounding 机制——告诉 Gemini "这次调用允许使用 google_search tool"。Gemini 内部决定要不要 search、搜几次、怎么 merge。**看不到 search 的中间步骤**——它在 one-shot invoke 里完成，不走 ReAct 的 thought/action/observation 多轮。这是为什么 Explorer 能"一次 invoke 返回一个带 grounding 的完整 draft"。

### 3.3 Critic — `graphs/refine.py:critic_node`

这是 Refine 阶段**最精密**的部分：

```python
def critic_node(state: RefineState) -> dict:
    prior_issues: list[Issue] = state.get("issues") or []
    feedback = critique_draft(state["draft"], prior_issues=prior_issues)

    resolved_set = set(feedback.resolved)
    carried = [i for i in prior_issues if i.id not in resolved_set]
    next_issues = carried + list(feedback.new_issues)

    blocker_count = sum(1 for i in next_issues if i.severity == "blocker")
    major_count = sum(1 for i in next_issues if i.severity == "major")
    passed = blocker_count == 0 and major_count <= 1

    return {
        "issues": next_issues,
        "resolved": feedback.resolved,  # appended via reducer
        "passed": passed,
    }
```

**三步**：

**第一步：调 Critic 拿增量反馈**。`critique_draft` 返回 `CritiqueFeedback`（Pydantic），包含 `resolved: list[str]`（这轮哪些 prior id 被解决了）+ `new_issues: list[Issue]`（这轮新发现的问题）+ `summary: str`。**注意 Critic 不返回 `passed` 字段，不返回 "全量当前 unresolved"**——这是和原 MAARS IterationState 对齐的设计。

**第二步：Python 合并 state**。

```python
carried = [i for i in prior_issues if i.id not in resolved_set]
next_issues = carried + list(feedback.new_issues)
```

公式：**`next = (prior - resolved) + new_issues`**。这就是 IterationState 的 diff apply。

**为什么这样做的几个好处**（见 incremental refactor commit `ac57d61`）：

- LLM 只判断"这轮变化了什么"，不需要重新记住所有 unresolved 问题
- 漏报新问题最多让 review 不严格，不会让旧问题静默丢失
- 职责清晰：Python 管状态，LLM 管判断

**第三步：Python 判 `passed`**。规则 `no blockers + ≤1 major`——这是确定性的 business rule，交给 Python 而不是 LLM。好处：

- rule 100% 一致，不会因为 LLM 心情好放水
- 不用让 Critic 自己判断（减轻 LLM 负担）
- 改 rule 只改 1 行 Python，不用重新调 prompt

**返回的 dict**：

- `issues: next_issues` — **没有 reducer**，LangGraph 直接覆盖 state.issues（这就是为什么 critic_node 能写"系统维护的完整 list"）
- `resolved: feedback.resolved` — **有 reducer** `Annotated[list[str], add]`，LangGraph 用 `operator.add` 把这轮的 resolved ids append 到 state.resolved 历史列表
- `passed: True/False` — 覆盖

### 3.4 `agents/critic.py:critique_draft()`

```python
def critique_draft(draft, *, prior_issues=None):
    model = get_chat_model(temperature=0.0)
    critic = model.with_structured_output(CritiqueFeedback)
    # ... build prior_section (context for this round) ...
    result = critic.invoke([("system", CRITIC_SYSTEM_PROMPT), ("human", user_message)])
    return result  # CritiqueFeedback instance
```

**`model.with_structured_output(CritiqueFeedback)`** 是 LangChain 的魔法——它把 Pydantic schema 转成 JSON schema 传给 Gemini 的 function-calling API，让模型按 schema 生成 JSON，LangChain 收到后自动 parse + validate 成 Pydantic instance。

**两个要注意的点**：

1. **`temperature=0.0`** — Critic 应该是确定性的 judge，不要有 creativity
2. **没有 grounding** — Critic 不需要 google_search（它只需要读 draft 判断），所以用 `get_chat_model` 而不是 `get_search_model`

### 3.5 Critic 的 prompt 结构

`prompts/critic.py:CRITIC_SYSTEM_PROMPT` 严格规定了：

- **职责分工**："系统维护完整 list，你只报增量" + "不要判断 passed"
- **5 个评审维度**：scope / variables / baseline / data / feasibility
- **id 命名规则**：`<维度>-<序号>`，新 id 不复用历史 resolved 的编号
- **severity 三级**：blocker / major / minor
- **风格**：直接、具体、有建设性、不恭维

user message（`agents/critic.py`）里的 prior_section 有两种形态：

- **首轮**: `"这是第一轮，没有 prior issues。resolved 留空，只关注 new_issues。"`
- **非首轮**: 列出完整的 prior issues（id + severity + summary + detail），明确说"系统已经维护了这份 list，你只需做 diff"

---

## 4. 条件边

**`graphs/refine.py:should_continue`**：

```python
def should_continue(state: RefineState) -> str:
    if state.get("passed", False):
        return END
    if state.get("round", 0) >= REFINE_MAX_ROUND:
        return END
    return "explorer"
```

LangGraph 的 conditional edge：函数返回 node name string 或 `END` 常量，graph 跳到对应节点。**三种情况**：

1. `passed=True` → END（正常收敛）
2. `round >= 5` → END（safety net）
3. 其他 → 回到 explorer 开始下一轮

---

## 5. State 类型

**`state.py`**：

```python
class Issue(BaseModel):  # Pydantic
    id: str
    severity: str      # "blocker" | "major" | "minor"
    summary: str
    detail: str

class RefineState(TypedDict, total=False):
    raw_idea: str
    draft: str
    issues: list[Issue]                      # overwrite per node
    resolved: Annotated[list[str], add]      # append via reducer
    round: int
    passed: bool
```

**两种数据模型并用**：

- **`Issue`** 是 `pydantic.BaseModel` — 因为它要作为 Critic 的 structured output 的 sub-type，LangChain 需要 Pydantic 才能生成 JSON schema
- **`RefineState`** 是 `typing.TypedDict` — LangGraph 原生要求 TypedDict（或 Pydantic）作为 state schema；TypedDict 更轻量，不带 validation 开销

**`Annotated[list[str], add]`** 是 LangGraph 的 reducer 语法：告诉 graph compile 时"对这个字段，用 `operator.add` 合并"——也就是 list 拼接。字段没有 `Annotated` 的就是默认覆盖语义。

**为什么 `issues` 用覆盖而不是 add**：Critic 返回的"next_issues"已经是系统维护后的完整 list，不是增量，不能再 add——否则会重复。具体讨论见 commit `ac57d61` 的讲解。

**`total=False`** 意味着所有字段都是 optional。初始 state 只传 `{"raw_idea": ..., "round": 0}`，其他字段由 node 逐步填。

---

## 6. Checkpointer 和 Session 落盘

这是两套**独立**的持久化：

### 6.1 LangGraph 的 checkpointer（运行时 state）

**`AsyncSqliteSaver`** 管理 `data/checkpoints.db`（单个 SQLite 文件）。LangGraph 在**每个 node 结束后**自动做一次 checkpoint——把整个 state 序列化（msgpack）写入 SQLite 的 `checkpoints` 表，按 `(thread_id, checkpoint_id)` 索引。

这让：

- **Resume** 能从最后一个成功 node 之后继续（中断 / crash / Ctrl-C 后）
- **Time-travel** 理论上可以看任意历史 checkpoint（MAARS 没用这个 feature）
- **并发安全** 因为 SQLite 有 atomic write

**`serde.JsonPlusSerializer(allowed_msgpack_modules=[("maars.state", "Issue")])`** 是安全 allowlist——LangGraph 1.x 出于安全考虑禁止反序列化未明确允许的自定义 Pydantic 类，必须显式把 `maars.state.Issue` 加进来，否则 checkpointer 读写会 emit warning（未来版本会直接 block）。

### 6.2 Session 落盘 — `cli.py:_save_refine_session`

跟 checkpointer 完全独立，是**人类可读**的 artifact dir：

```
data/refine/{sub}/
├── raw_idea.md      # 用户原始输入
├── draft.md         # 最终 refined draft
├── issues.json      # 剩余 unresolved issues (结构化)
└── meta.json        # 元数据（timing / usage / rounds / passed / interrupted）
```

`{sub}` 是 thread_id 剥掉 `refine-` 前缀后的部分（`refine-001` → `001`，`verify-stream` → `verify-stream`），由 `_session_dir_for()` 计算。

**`meta.json` 的完整 schema**：

```json
{
  "thread_id": "refine-001",
  "started_at": "2026-04-12T02:30:15.123456+00:00",
  "finished_at": "2026-04-12T02:34:22.789012+00:00",
  "duration_seconds": 247.666,
  "model": "gemini-3-flash-preview",
  "max_round": 5,
  "final_round": 5,
  "passed": false,
  "interrupted": false,
  "total_resolved": 17,
  "remaining_issues": {"blocker": 0, "major": 2, "minor": 1},
  "usage": {
    "total_tokens": 28456,
    "input_tokens": 19234,
    "output_tokens": 9222,
    "by_node": {
      "explorer": {"input_tokens": 12000, "output_tokens": 6000, "total_tokens": 18000},
      "critic":   {"input_tokens": 7234,  "output_tokens": 3222, "total_tokens": 10456}
    }
  }
}
```

`issues.json` 是 `[Issue.model_dump(), ...]` 的 list，每个 issue 带 `id / severity / summary / detail`。

---

## 7. 关键设计决策

**1. 增量 feedback，不是快照** — `critic_node` 在 Python 层应用 diff（`prior - resolved + new_issues`），Critic LLM 只报变化。这对齐原 MAARS IterationState，避免 LLM 忘记旧 issue 导致状态漂移。见 commit `ac57d61`。

**2. Python 判 `passed`，不是 LLM** — `passed` 规则 `no blockers + ≤1 major` 是确定性的，交给 LLM 会引入 "Critic 凭感觉 pass" 的风险。Python 规则 1 行代码，100% 一致。

**3. Explorer 用 Gemini grounding，不用 ReAct + Tavily** — one-shot invoke 就能拿到带 web search 的 draft，不走多轮 thought/action loop，代码更简单，stream event 更少，不需要外部 search API key。代价是 Explorer 绑定 Gemini provider。见 commit `03350c1`。

**4. `with_structured_output(CritiqueFeedback)` 而不是 prompt parsing** — LangChain 把 Pydantic schema 转成 Gemini function-calling schema，模型直接返回 JSON，LangChain 自动 validate。省掉手写 JSON regex + retry 的 boilerplate，而且类型安全。

**5. Thread id 自动递增而非时间戳** — 时间戳（`20260412-023015`）难读；UUID（`refine-a3b7c2d4`）无序；递增编号（`refine-001` / `refine-002`）可读 + 按时间有序 + 永不冲突。用户看 `ls data/refine/` 就是一个清晰的历史 timeline。

**6. Session 目录和 checkpoint DB 分离** — `data/checkpoints.db` 是 LangGraph 的 runtime state（紧凑 msgpack，机器读），`data/refine/{NNN}/` 是 human-readable artifacts。两套独立持久化，职责清晰，即使清空 checkpoint 用户还能看到历史 session 的 draft。

**7. ESC 监听通过 cbreak + add_reader 实现，而不是 Ctrl-C** — Ctrl-C 发送 SIGINT，是 OS 级中断；ESC 是普通字符，需要把 stdin 放在 non-canonical mode 才能立即读到。`asyncio.add_reader(fd, callback)` 是非阻塞的 fd 监听，不占用 event loop。Windows / non-TTY 自动 fallback 到"no-op listener + Ctrl-C only"。

---

## 8. 几个值得注意的 gotcha

**1. Gemini 3 返回的 AIMessage.content 是 list of content blocks**，不是 str。

```python
content = response.content  # 可能是 [{"type": "text", "text": "..."}, ...]
```

所以 `agents/explorer.py` 和 `cli.py:sanity()` 都有 defensive 的 `isinstance(content, list)` 检查 + 提取 text blocks。新加 agent 时记得复用这个 pattern。

**2. Critic 的 token 消耗比 Explorer 多 ~2×** — 从实测看：

- Critic input 大：要带 prior issues 列表 + draft
- Critic output 大：`with_structured_output` 让 Gemini 把 schema 定义也算进 output token

如果想优化，可以考虑 (a) 让 Critic 用更便宜的 Gemini 变体；(b) 精简 CritiqueFeedback schema；(c) 限制 prior_issues 的 detail 长度。

**3. `thread_id: str = typer.Option(None, ...)`** 的 type hint 是 `str` 但 default 是 `None` — 技术上应该是 `Optional[str]`，但 typer 对 Option 的 None default 有特殊处理，实际工作正常。属于小 type hint 不严，不影响运行。

**4. 每轮 Critic 的 input 会增长** — 因为要传 prior_issues，而 issues 数量通常稳定在 3-5 个。但如果某一轮 new_issues 爆炸（比如 10 个），后续轮次的 prompt 会变长。目前没有 token budget 限制，但 5 轮是硬上限保护。

**5. Rich Status 和 `astream_events` 的并发** — spinner 在独立线程跑，`console.print` 在主协程。Rich 的 Live 有 lock 机制保证不打架，但如果 spinner 没 stop 就 print 会有 race。代码严格遵守 "先 `current_status.stop()` 再 `console.print(...)`" 的顺序。

---

## 9. 文件清单（实际代码量）

| 文件 | 行数 | 作用 |
|---|---|---|
| `src/maars/cli.py` | ~500 | typer 命令 + `_refine_async` + 所有 CLI 层 helper |
| `src/maars/graphs/refine.py` | ~87 | `StateGraph` 构建 + 2 node + 条件边 |
| `src/maars/agents/explorer.py` | ~66 | `draft_proposal()` + 两种 prompt mode |
| `src/maars/agents/critic.py` | ~100 | `CritiqueFeedback` + `critique_draft()` |
| `src/maars/prompts/explorer.py` | ~45 | Explorer system prompt |
| `src/maars/prompts/critic.py` | ~55 | Critic system prompt |
| `src/maars/models.py` | ~36 | `get_chat_model()` / `get_search_model()` |
| `src/maars/state.py` | ~30 | `Issue` + `RefineState` |
| `src/maars/config.py` | ~17 | env vars + paths |

**核心实现总共不到 1000 行**。其中 cli.py 占了一半（因为它包含 CLI 层的所有 UX：auto thread id、spinner、ESC、session save、usage tracking）。真正的 **graph 逻辑只有 ~200 行**（agents + graphs + prompts）。
