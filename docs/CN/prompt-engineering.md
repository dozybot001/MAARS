# Prompt 工程文档

## Prompt 架构

MAARS 的两种模式使用**独立的 prompt 体系**：

```
Gemini/Mock 模式                     Agent 模式
─────────────                       ─────────
Pipeline System Prompt               Agent Instruction
  职责：流程编排、轮次目标              职责：完整任务描述、工具使用、行为约束
  位置：backend/pipeline/*.py          位置：backend/agent/__init__.py
  注入：build_messages() system role   注入：create_agent(instruction=...)
```

### 设计原则

- **Gemini/Mock**：无工具能力，pipeline 通过多轮 prompt 手把手编排（Explore → Evaluate → Crystallize）
- **Agent**：有工具能力，instruction 描述完整任务目标和参考流程，Agent 自主决定执行步骤
- Agent instruction 参考了 pipeline 的流程设计（如 Explore/Evaluate/Crystallize），但不依赖 pipeline prompt，是**独立编写的完整任务描述**
- Plan 和 Execute 阶段两种模式共用 pipeline stage，Agent 的 instruction 与 pipeline system prompt 通过 `AgentClient._build_agent_prompt()` 合并

## Pipeline 层 Prompt 清单

### 通用前缀

所有 pipeline prompt 共享 `_AUTO` 前缀：

```
This is a fully automated pipeline. No human is in the loop.
Do NOT ask questions or request input. Make all decisions autonomously.
全文使用中文撰写。
```

### Refine（3 轮）

| 轮次 | 标签 | 目标 |
|------|------|------|
| 0 | Explore | 发散：识别子领域、调研现状、发散方向 |
| 1 | Evaluate | 收敛：三维评估（新颖性/可行性/影响力），选定方向 |
| 2 | Crystallize | 产出：完整研究提案（标题/问题/方法/贡献） |

位置：`backend/pipeline/refine.py` → `_PROMPTS[]`

### Plan（模板 + 可替换原子定义）

模板 `_SYSTEM_PROMPT_TEMPLATE` 包含：
- 流水线上下文（4 阶段说明，Write 阶段负责写论文）
- `{atomic_definition}` 占位符 ← 适配器注入
- 规则：依赖、并行、JSON 格式

原子定义由模式决定：

| 模式 | 原子标准 |
|------|---------|
| Gemini/Mock | 单次 LLM 调用能产出可靠结果 |
| Agent | 单个 Agent session 能端到端完成（含多次工具调用） |

位置：`backend/pipeline/plan.py` → `_SYSTEM_PROMPT_TEMPLATE` + `_ATOMIC_DEF_DEFAULT`
Agent 原子定义：`backend/agent/__init__.py` → `agent_atomic_def`

### Execute（2 个 prompt）

| Prompt | 用途 |
|--------|------|
| `_EXECUTE_SYSTEM` | 任务执行：产出有深度的结果 |
| `_VERIFY_SYSTEM` | 质量验证：判断是否实质达成目标（务实不教条） |

位置：`backend/pipeline/execute.py`

### Write（3 个 prompt）

| Prompt | 阶段 | 用途 |
|--------|------|------|
| `_OUTLINE_SYSTEM` | Outline | 设计论文大纲，映射任务到章节 |
| `_SECTION_SYSTEM` | Sections | 基于任务产出写单个章节 |
| `_POLISH_SYSTEM` | Polish | 润色全文，统一术语和风格 |

位置：`backend/pipeline/write.py`

## Agent Instruction 清单

Agent 模式的 Refine 和 Write 使用独立的 stage（`AgentRefineStage`、`AgentWriteStage`），instruction 是完整的任务描述，**不拼接 pipeline prompt**。

| 指令 | 用于阶段 | Stage 类 | 核心内容 |
|------|---------|---------|---------|
| `_REFINE_INSTRUCTION` | Refine | `AgentRefineStage` | 完整任务：Explore → Evaluate → Crystallize，强制使用搜索工具 |
| `_EXECUTE_INSTRUCTION` | Execute | `ExecuteStage`（共用） | **强制使用工具**：MUST call code_execute，不伪造 |
| `_WRITE_INSTRUCTION` | Write | `AgentWriteStage` | 完整任务：读取所有产出、设计结构、撰写全文 |
| `agent_atomic_def` | Plan | `PlanStage`（共用） | Agent 的原子任务定义（注入 Plan 模板） |

位置：`backend/agent/__init__.py`（instruction）、`backend/agent/stages.py`（stage 类）

**注意**：Agent instruction 参考了 pipeline 的流程步骤作为指引（如 Refine 的三阶段），但 Agent 在单个 session 中自主决定执行顺序和深度，不受 pipeline 多轮机制约束。

## 完整 Prompt 示例

### Agent 模式 — Refine（单 session）

```
[ADK System Instruction]
You are a research advisor. Your job is to take a vague research idea
and refine it into a complete, actionable research proposal.

Work autonomously through these phases — do NOT stop early:
1. Explore: Search for relevant papers and survey the landscape...
2. Evaluate: Based on your research, evaluate possible directions...
3. Crystallize: Produce a finalized research idea document...

IMPORTANT: You MUST use your search and paper-reading tools...
全文使用中文撰写。Output in markdown.

[User Message]
用蒙特卡洛方法估算圆周率：不同采样数量对收敛速度的影响
```

### Agent 模式 — Execute 某任务

```
[ADK System Instruction]
You are a research assistant executing a specific task...
（_EXECUTE_INSTRUCTION + pipeline _EXECUTE_SYSTEM 合并）

[User Message]
## Prerequisite tasks (use read_task_output to read): 1_1, 1_2
---
## Your task [2_1]:
实现蒙特卡洛采样算法并绘制收敛曲线
```

### Gemini 模式 — Execute 某任务

```
[System Instruction]
This is a fully automated pipeline...
You are a research assistant executing a specific task...
Output in markdown.

[User Message]
## Context from completed prerequisite tasks:
### Task [1_1] output:
（完整的依赖任务内容，预加载在 prompt 中）
---
## Your task [2_1]:
实现蒙特卡洛采样算法并绘制收敛曲线
```

## 修改指南

| 要改什么 | 改哪里 |
|---------|--------|
| Gemini/Mock 某阶段的流程逻辑 | `pipeline/*.py` 的 system prompt |
| Agent Refine/Write 的任务描述 | `agent/__init__.py` 的 `_REFINE_INSTRUCTION` / `_WRITE_INSTRUCTION` |
| Agent Execute 的工具约束 | `agent/__init__.py` 的 `_EXECUTE_INSTRUCTION` |
| 原子任务标准 | Gemini: `pipeline/plan.py` → `_ATOMIC_DEF_DEFAULT`；Agent: `agent/__init__.py` → `agent_atomic_def` |
| 全局自动化约束（Gemini） | `pipeline/refine.py` 的 `_AUTO`（其他 pipeline 文件同名变量） |
| Agent Refine/Write 的 stage 行为 | `agent/stages.py` 的 `AgentRefineStage` / `AgentWriteStage` |
| Verify 严格度 | `pipeline/execute.py` 的 `_VERIFY_SYSTEM`（两种模式共用） |
