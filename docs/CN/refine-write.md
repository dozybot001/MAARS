# Refine / Write 阶段详情

中文 | [English](../EN/refine-write.md)

> 回到 [架构概览](architecture.md)

Refine 和 Write 共享同一个 `TeamStage` 基类，使用 `IterationState` 驱动的 Multi-Agent 循环。两者完全对称，仅配置不同。Write 之后还有一个独立的 **Polish** 阶段，用于单次打磨。

## 1. IterationState

```python
@dataclass
class IterationState:
    draft: str              # 最新一版完整内容（提案/论文）
    issues: list[dict]      # [{section, problem, suggestion}]
    iteration: int          # 当前轮次
    _next_id: int = 1       # Issue ID 自增计数器（I1, I2, I3...）
```

**状态更新规则**：
- `draft`：每轮由 primary agent 产出，直接覆盖
- `issues`：reviewer 输出 `resolved` 列表 -> 按系统分配的 ID 移除；reviewer 输出 `issues` 列表 -> 系统自动分配 ID（I1, I2, ...）并追加
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
    feedback = parse_json_fenced(review)         # {issues, resolved}
    save_round_md(reviewer_dir, review, round)   # 落盘
    save_round_json(reviewer_dir, feedback, round)
    send()                                       # done signal

    state.update(draft, feedback)                # issues = 去 resolved + 自动分配 ID 给新 issue
    if not state.issues: break                   # issues 列表为空 = 通过

# 若达到 max_delegations 仍有未解决 issues：
# 记录警告日志，使用最后一版 draft 继续流水线
```

每轮 2 次 LLM 调用。Reviewer 通过 `_REVIEWER_OUTPUT_FORMAT` 输出 JSON 结构化反馈。系统（而非 reviewer）通过检查 `issues` 列表是否为空来判定通过。Runtime 机械执行状态更新并自动分配 issue ID（I1, I2, ...）——状态管理不涉及 LLM。当达到 `max_delegations` 时，系统记录警告日志并使用最后一版 draft 继续流水线。

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
  Critic(idea + v1)                        -> {issues:[A,B,C]}
  系统分配 ID: I1=A, I2=B, I3=C
  state = {draft: v1, issues: [I1,I2,I3], iteration: 1, _next_id: 4}

Round 2:
  Explorer(idea + v1 + [I1,I2,I3])         -> draft v2
  Critic(idea + v2 + [I1,I2,I3])           -> {issues:[D], resolved:[I1,I2]}
  系统分配 ID: I4=D；移除 I1, I2
  state = {draft: v2, issues: [I3,I4], iteration: 2, _next_id: 5}

Round 3:
  Explorer(idea + v2 + [I3,I4])            -> draft v3
  Critic(idea + v3 + [I3,I4])              -> {issues:[], resolved:[I3,I4]}
  issues 为空 -> 通过
  break -> save refined_idea.md / paper.md
```

## 5. Reviewer JSON 格式

```json
{
  "issues": [
    {
      "section": "Methodology",
      "problem": "DAG extraction feasibility unclear",
      "suggestion": "Add human-in-the-loop validation step"
    }
  ],
  "resolved": ["I1", "I3"]
}
```

- `issues`：本轮新发现的问题（无需 `id`、`severity`，由系统自动分配 ID）
- `resolved`：引用上方 "Previously Identified Issues" 中已修复的系统分配 ID（如 I1, I3）
- 通过判定：系统在状态更新后检查 `issues` 列表是否为空，为空即通过（无需 `pass` 字段）
- `format_issues()` 输出中每个 issue 以 `**I{n}**` 前缀标识，确保 reviewer 能准确引用

## 6. 与 Research 的对比

| | Research | Refine / Write |
|---|---|---|
| 循环 | strategy -> decompose -> execute -> evaluate | primary -> reviewer -> primary -> reviewer |
| 状态 | task_results + plan_tree + score | IterationState (draft + issues) |
| 编排者 | Python `_run_loop` | Python `TeamStage._execute` |
| Agent 角色 | 每个 task 独立 Agent | 两个固定角色交替 |
| 通信方式 | 通过 artifacts/DB | 通过 IterationState 注入 prompt |
| 持久化 | checkpoint/resume | checkpoint/resume（每轮落盘） |
| 终止条件 | Evaluate 无 strategy_update | issues 列表为空或达到 max_delegations（警告 + 继续） |

核心模式一致：**Python 控制流程，Agent 只负责执行单步，状态在 runtime 层管理。**

## 7. Polish 阶段

PolishStage 继承自 `Stage`（而非 `TeamStage`），在 Write 完成之后运行。不涉及多 Agent 循环。

**流程**：
1. 单次 LLM 调用：对 `paper.md` 进行最终打磨（语法、格式、一致性）
2. 附加元数据附录（生成日期、模型、配置等）
3. 输出最终 `paper.md`

**设计要点**：
- 单 Agent、单次调用，无 reviewer 循环
- 继承 `Stage` 而非 `TeamStage`，不使用 `IterationState`
- 不改变论文内容结构，只做表面层打磨

## 8. 代码位置

| 文件 | 职责 |
|---|---|
| `backend/team/stage.py` | TeamStage 基类 + IterationState |
| `backend/team/refine.py` | RefineStage 配置 |
| `backend/team/write.py` | WriteStage 配置 |
| `backend/team/polish.py` | PolishStage 配置 |
| `backend/team/prompts_en.py` | EN prompts + `_REVIEWER_OUTPUT_FORMAT` |
| `backend/team/prompts_zh.py` | ZH prompts |
