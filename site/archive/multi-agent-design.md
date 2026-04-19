# 多智能体架构设计

> 设计文档，尚未实施。描述从 orchestrated pipeline 演进到真正多智能体系统的目标架构。

## 现状 vs 目标

| | 现状（Adaptive DAG Orchestrator） | 目标（Multi-Agent） |
|---|---|---|
| 控制流 | Python 硬编码（if/for/while） | Orchestrator Agent ReAct 自主决策 |
| 方向选择 | 单 LLM Refine（3 轮） | Scholar 调研 + Critic 质疑 + Orchestrator 决策 |
| 任务分解 | 递归 LLM 调用 | 不变（decompose 作为 Orchestrator 的工具） |
| 任务执行 | 并行 Worker（不变） | 不变 + Worker 可查询 Scholar |
| 验证 | 单次 LLM 判定 | Critic 多轮交叉质询 |
| 跨任务关联 | 无 | Scholar 综合分析 |
| 论文评审 | 5-phase 自审 | Critic 模拟同行评审 |

## 三个持久 Agent

### Orchestrator（策略 + 调度）

中央决策 agent。不执行研究任务，而是决定做什么、何时做、谁来做。

- 运行方式：单个 ReAct session，通过工具调用其他 agent
- 工具集：consult_scholar、request_critique、decompose、dispatch_workers、emit_phase、write_paper、DB tools、code_execute
- 系统 prompt 提供工作流指引（refine→research→write），但不强制顺序
- 可自由回退（Critic 否决论文 → 回到 research 补充实验）

### Scholar（知识中枢）

持久知识 agent。在整个研究过程中积累领域知识。

- 持久状态：对话历史 + 知识摘要存入 `knowledge/` 目录
- 工具：搜索（google_search/DuckDuckGo）、论文获取（fetch/arXiv）
- 被调用方式：Orchestrator 调 `consult_scholar(question)`，Worker 调 `query_scholar(question)`
- 参与环节：
  1. Refine 前 — 文献调研，提供领域全景
  2. Execute 中 — 被 Worker 查询相关知识
  3. Execute 后 — 跨任务综合，发现矛盾和关联
  4. Write 时 — 提供引用和领域上下文

### Critic（对抗者）

持久审查 agent。始终试图找出问题。越来越严格。

- 持久状态：审查历史存入 `reviews/` 目录，对话历史中包含之前的审批记录
- 工具：无外部工具（纯推理审查）
- 被调用方式：Orchestrator 调 `request_critique(content, context)`
- 参与环节：
  1. 方向选择后 — 质疑研究方向可行性和新颖性
  2. 任务执行后 — 交叉质询（多轮对话，替代当前单次 verify）
  3. 论文写完后 — 模拟同行评审
- 严格度递增：系统 prompt 中包含已审批数量，要求越来越高

### 临时 Worker

与现有设计相同：独立 LLM/Agent session，执行单个研究任务。

- 无持久状态
- 工具：搜索、code_execute、query_scholar
- 并行执行，按拓扑排序分批

## 通信方式：Tool-Based

Agent 间通信通过工具调用实现，不需要消息总线。

```
Orchestrator 调用 consult_scholar("这个领域的最新进展？")
  → Scholar.invoke() 内部运行 LLM session
  → Scholar 搜索文献，积累对话历史
  → 返回回答文本
  → Orchestrator 继续 ReAct 循环

Orchestrator 调用 request_critique(worker_result, task_description)
  → Critic.invoke() 内部运行 LLM session
  → Critic 审查结果，可能提出问题
  → 返回结构化审查: {"verdict": "pass|revise|reject", "feedback": "..."}
  → Orchestrator 根据 verdict 决定下一步
```

优点：
- 无需新协议或消息总线
- 复用现有 LLMClient.stream() 基础设施
- Orchestrator 看到的就是工具调用结果，符合 ReAct 模式
- 所有 StreamEvent 自然流向前端

## 核心抽象：PersistentAgent

```python
class PersistentAgent:
    """包装 LLMClient，维护跨调用的对话历史。"""

    name: str                   # "orchestrator" | "scholar" | "critic"
    system_prompt: str          # 角色定义
    llm_client: LLMClient       # AgnoClient
    history: list[dict]         # 累积对话
    db: ResearchDB              # 持久化

    async def invoke(message: str) -> str
        # 构建 messages: system + history + user
        # stream via llm_client
        # 追加到 history
        # 广播事件
        # 返回 response

    def save_checkpoint()       # 持久化到 agent_state/
    def load_checkpoint()       # 从 DB 重建（resume 用）
```

所有 Agent 都是 PersistentAgent 实例，区别在于 system_prompt 和工具集。框架无关——基于 LLMClient 抽象，4 种模式全部支持。

## AgentSession（替代 PipelineOrchestrator）

```python
class AgentSession:
    """管理多 Agent 研究 session。"""

    db: ResearchDB
    orchestrator: PersistentAgent
    scholar: PersistentAgent
    critic: PersistentAgent
    _subscribers: list[asyncio.Queue]    # SSE

    async def start(research_input: str)
        # 创建 DB session
        # 实例化 3 个 Agent
        # 构建 Orchestrator 工具集
        # 运行 Orchestrator ReAct session

    async def stop() / resume() / retry()
```

## 前端兼容

保留现有 3 卡片 UI（Refine / Research / Write）。Orchestrator 通过 `emit_phase("research")` 工具触发 SSE state 事件，前端无感切换。

新增 SSE 事件（可选，不影响现有功能）：

| 事件 | 数据 | 用途 |
|------|------|------|
| `agent_state` | `{agent: "scholar", status: "searching"}` | 显示活跃 Agent |
| `agent_message` | `{from: "critic", to: "orchestrator", summary: "..."}` | Agent 间通信日志 |

## DB 扩展

```
results/{id}/
  knowledge/          # Scholar 知识积累
    k_{n}.md
  reviews/            # Critic 审查记录
    r_{n}.json
  agent_state/        # Agent checkpoint
    orchestrator.json
    scholar.json
    critic.json
```

## 典型运行流

```
1. 用户输入 idea

2. Orchestrator → emit_phase("refine")
   Orchestrator → consult_scholar("调研领域现状和最新进展")
     Scholar: 搜索文献 → 积累知识 → 返回领域全景
   Orchestrator → consult_scholar("基于调研，评估 3 个可能的研究方向")
     Scholar: 返回方向分析
   Orchestrator → request_critique("我选择方向 A，理由是...")
     Critic: "方向 A 新颖性不足，X 团队 2025 年做过类似的"
   Orchestrator → consult_scholar("确认 X 团队的工作")
     Scholar: "确实存在，但没覆盖 Y 方面"
   Orchestrator: 调整方向，聚焦 Y
   → 保存 refined_idea.md

3. Orchestrator → emit_phase("research")
   Orchestrator → decompose(refined_idea)
     → 返回任务 DAG
   Orchestrator → dispatch_workers(tasks_batch_1)
     → 并行执行，Worker 可查询 Scholar
     → 返回结果摘要
   Orchestrator → request_critique(task_1_result)
     Critic: "方法论有缺陷，步长选择没有覆盖 stiff 区域"
   Orchestrator → dispatch_workers(revised_task_1)  # 重新执行
   Orchestrator → request_critique(revised_result)
     Critic: "通过"
   ... 继续所有任务 ...
   Orchestrator → consult_scholar("综合所有结果，有没有跨任务的矛盾？")
     Scholar: "task_3 和 task_7 的结论不一致"
   Orchestrator → dispatch_workers(reconciliation_task)

4. Orchestrator → emit_phase("write")
   Orchestrator → write_paper()
   Orchestrator → request_critique(paper_draft)
     Critic: "方法论部分没有讨论局限性，引用不够充分"
   Orchestrator → consult_scholar("补充相关引用")
   Orchestrator: 修改论文
   Orchestrator → request_critique(revised_paper)
     Critic: "通过"
   → 保存 paper.md
```

## 实施路径

| 阶段 | 内容 | 复杂度 |
|------|------|--------|
| Phase 1 | PersistentAgent + AgentSession + DB 扩展 | 低 |
| Phase 2 | Scholar + Critic + 跨 Agent 工具 | 中 |
| Phase 3 | Orchestrator + Worker + 完整工具集 | 高 |
| Phase 4 | 前端扩展 + 路由适配 | 中 |
| Phase 5 | 模式支持 + Resume/Retry + 稳定性 | 中 |

旧 pipeline 通过 git tag `v8.2.0` 保留为 fallback。

## 风险

| 风险 | 缓解 |
|------|------|
| Orchestrator context 爆满 | Scholar/Critic 返回摘要；Worker 结果存 DB |
| 工作流不确定性 | 系统 prompt 强指引 + emit_phase 审计 + 最大迭代防护 |
| Agent 间调用延迟 | 同模型实例、简洁 prompt、response 限长 |
| 调试困难 | 全部 Agent 通信作为 SSE 事件可视化 |

## 与现有架构的关系

现有的 Adaptive DAG Orchestrator 不会被废弃——它的核心组件（decompose、topological_batches、DB 工具、Docker 工具、SSE 广播）全部被多智能体架构复用。多智能体架构是在其上的**策略层升级**：把硬编码的决策逻辑替换为 Agent 自主决策，把单次验证替换为多轮对抗审查，把孤立执行替换为知识共享。
