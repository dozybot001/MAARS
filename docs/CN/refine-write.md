# Refine / Write 阶段详情

> 回到 [架构概览](architecture.md)

Refine 和 Write 共享同一个 `TeamStage` 基类，使用 `IterationState` 驱动的双 Agent 循环。两者完全对称，仅配置不同。

## 1. IterationState

```python
@dataclass
class IterationState:
    draft: str              # 最新一版完整内容（提案/论文）
    issues: list[dict]      # [{id, severity, section, problem, suggestion}]
    iteration: int          # 当前轮次
```

**状态更新规则**：
- `draft`：每轮由 primary agent 产出，直接覆盖
- `issues`：reviewer 输出 `resolved` 列表 -> 按 id 移除；reviewer 输出 `issues` 列表 -> 追加
- `iteration`：每轮 +1

**上下文注入**：IterationState 不是 Agent 可感知的对象，通过 `_build_primary_prompt()` / `_build_reviewer_prompt()` 拼接到 user_text 中。每轮 Agent 收到的上下文大小恒定（原始输入 + 最新 draft + 未解决 issues），不随迭代轮数增长。

## 2. 循环机制

```python
for round in range(max_delegations):
    # 1. Primary agent 产出/修订
    draft = _stream_llm(primary_agent, input + state)
    state.draft = draft
    save_round_md(primary_dir, draft, round)    # 落盘
    send()                                       # done signal

    # 2. Reviewer 评审
    review = _stream_llm(reviewer_agent, input + state)
    feedback = parse_json_fenced(review)         # {pass, issues, resolved}
    save_round_md(reviewer_dir, review, round)   # 落盘
    save_round_json(reviewer_dir, feedback, round)
    send()                                       # done signal

    if feedback.pass: break
    state.update(draft, feedback)                # issues = 去 resolved + 加 new
```

每轮 2 次 LLM 调用。Reviewer 通过 `_REVIEWER_OUTPUT_FORMAT` 输出 JSON 结构化反馈，runtime 机械执行状态更新。

## 3. Refine vs Write 配置对比

| | Refine | Write |
|---|---|---|
| Primary agent | Explorer（搜索工具：arXiv, Wikipedia） | Writer（DB 工具：list_tasks, read_task_output, list_artifacts） |
| Reviewer agent | Critic（搜索工具） | Reviewer（DB 工具 + list_artifacts） |
| 输入 | `db.get_idea()` 原始文本 | 静态指令（Writer 自己调工具读数据） |
| 输出 | `refined_idea.md` | `paper.md` |
| 落盘目录 | `proposals/` + `critiques/` | `drafts/` + `reviews/` |
| SSE phase | `proposal` / `critique` | `draft` / `review` |
| 前端标签 | Proposals / Critiques / Final | Drafts / Reviews / Final |
| Gemini Search | 启用（`search=True`） | 启用 |

## 4. 典型 IterationState 生命周期

```
Round 1:
  Explorer(idea)                           -> draft v1
  Critic(idea + v1)                        -> {pass:false, issues:[A,B,C]}
  state = {draft: v1, issues: [A,B,C], iteration: 1}

Round 2:
  Explorer(idea + v1 + [A,B,C])            -> draft v2
  Critic(idea + v2 + [A,B,C])              -> {pass:false, issues:[D], resolved:[A,B]}
  state = {draft: v2, issues: [C,D], iteration: 2}

Round 3:
  Explorer(idea + v2 + [C,D])              -> draft v3
  Critic(idea + v3 + [C,D])                -> {pass:true}
  break -> save refined_idea.md / paper.md
```

## 5. Reviewer JSON 格式

```json
{
  "pass": false,
  "issues": [
    {
      "id": "feasibility_1",
      "severity": "major",
      "section": "Methodology",
      "problem": "DAG extraction feasibility unclear",
      "suggestion": "Add human-in-the-loop validation step"
    }
  ],
  "resolved": ["novelty_1", "scope_2"]
}
```

- `pass`：仅当无 major issue 时为 true
- `issues`：当前所有问题（新发现 + 仍未解决的旧问题）
- `resolved`：仅引用上方 "Previously Identified Issues" 中已修复的 id
- `format_issues()` 输出中每个 issue 以 `**id**` 前缀标识，确保 reviewer 能准确引用

## 6. 与 Research 的对比

| | Research | Refine / Write |
|---|---|---|
| 循环 | strategy -> decompose -> execute -> evaluate | primary -> reviewer -> primary -> reviewer |
| 状态 | task_results + plan_tree + score | IterationState (draft + issues) |
| 编排者 | Python `_run_loop` | Python `TeamStage._execute` |
| Agent 角色 | 每个 task 独立 Agent | 两个固定角色交替 |
| 通信方式 | 通过 artifacts/DB | 通过 IterationState 注入 prompt |
| 持久化 | checkpoint/resume | 每轮落盘，最终产物持久化 |
| 终止条件 | Evaluate 无 strategy_update | Reviewer pass=true 或达到 max_delegations |

核心模式一致：**Python 控制流程，Agent 只负责执行单步，状态在 runtime 层管理。**

## 7. 代码位置

| 文件 | 职责 |
|---|---|
| `backend/team/stage.py` | TeamStage 基类 + IterationState |
| `backend/team/refine.py` | RefineStage 配置 |
| `backend/team/write.py` | WriteStage 配置 |
| `backend/team/prompts_en.py` | EN prompts + `_REVIEWER_OUTPUT_FORMAT` |
| `backend/team/prompts_zh.py` | ZH prompts |
