# Research 阶段详情

中文 | [English](../EN/research.md)

> 回到 [架构概览](architecture.md)

Research 是 MAARS 的核心阶段。Runtime 编排任务分解、并行执行、验证和迭代评估，Agent 在 Docker 沙箱中执行每个原子任务。

## 1. 前置条件

`_preflight_docker` 在 `_execute()` 最开始检查：
- Docker SDK 已安装（`pip install docker`）
- Docker daemon 可达（`client.ping()`）
- `MAARS_DOCKER_SANDBOX_IMAGE` 镜像已构建（默认 `maars-sandbox:latest`）

不满足直接报错，不浪费后续的 calibrate token。

## 2. 原则

- 每轮 LLM 带能力画像 `_build_capability_profile`（沙箱配置 + 可用工具列表）
- 链路：Calibrate -> Strategy -> Decompose -> Execute -> Evaluate，上下文显式传递
- `plan_tree.json` 是唯一真值，`plan_list.json` 是派生缓存

## 3. 关键环节

### Calibrate（一次性）

| 项 | 内容 |
|---|---|
| 输入 | 能力画像 + 数据集 + 研究课题 |
| 输出 | 原子定义（3-5 句），注入 Decompose system prompt |
| 存储 | `calibration.md` |

### Strategy（每轮）

| 项 | 内容 |
|---|---|
| 输入 | 能力画像 + 数据集 + 原子定义 + 研究课题（首轮）/ 旧策略 + 评估反馈（后续轮） |
| 输出 | 策略文档 + score_direction |
| 存储 | `strategy/round_N.md` |

### Decompose（每轮）

| 项 | 内容 |
|---|---|
| 输入 | 研究课题（或迭代上下文）+ 原子定义 + 策略 + 兄弟上下文 |
| 输出 | 扁平任务列表 + 树结构 |
| 存储 | `plan_tree.json` + `plan_list.json` |
| 机制 | 递归分解、`root_id` 支持任意节点、可调用搜索/阅读工具 |

### Execute（每个任务，可并行）

| 项 | 内容 |
|---|---|
| 输入 | 任务描述 + 沙箱约束 + 依赖摘要 |
| 输出 | Markdown 结果 + artifacts + SUMMARY 行 |
| 存储 | `tasks/{id}.md` + `artifacts/{id}/` |
| 机制 | `asyncio.gather` 并行 + Semaphore（`api_concurrency`）控制并发 |

### Verify（每个任务）

| 项 | 内容 |
|---|---|
| 输入 | 任务描述 + 执行结果 |
| 输出 | `{pass, review, redecompose}` |
| 机制 | 鼓励调用 list_artifacts 验证；fallback=`pass:false` |
| 路径 | pass -> 完成 / retry -> 重新执行 / redecompose -> 拆分为子任务 |

### Evaluate（每轮）

| 项 | 内容 |
|---|---|
| 输入 | 研究目标 + 策略 + 分数趋势 + 历史评估 + 能力画像 + 任务摘要 |
| 输出 | `{feedback, suggestions, strategy_update?}` |
| 存储 | `evaluations/round_N.json` + `evaluations/round_N.md` |
| 机制 | `strategy_update` 存在 -> 继续迭代；`is_final` -> 总结不继续 |

## 4. 主循环骨架

```python
async def _execute(self):
    await _preflight_docker()

    await _calibrate_once(idea)     # 一次性

    evaluation = None
    while True:
        Strategy(idea, evaluation?)
        Decompose(idea, strategy)
        Execute(tasks)               # 并行，含 verify/retry/redecompose
        Evaluate(results, score)
        if not strategy_update: break
        iteration += 1
```

## 5. 关键决策

| 决策 | 选择 |
|---|---|
| 迭代控制 | Evaluate 输出 `strategy_update` 决定是否继续 |
| 迭代反馈 | Strategy 更新后重新 Decompose |
| 粒度校准 | 能力画像 + LLM（Calibrate 阶段） |
| 重分解 | `decompose(root_id=task_id)` |
| Summary | Execute agent 写 SUMMARY 行，供下游引用 |
| 验证 fallback | `pass=False` |
| 数据真值 | `plan_tree.json`；`plan_list.json` 派生 |

## 6. 并行执行模式

```python
# 拓扑排序分批
batches = topological_batches(tasks)   # 尊重依赖 DAG

for batch in batches:
    results = await asyncio.gather(
        *[execute_task(t) for t in pending],
        return_exceptions=True,
    )
```

每个 `execute_task` 内部通过 `_get_api_semaphore()` 控制 LLM 并发数（`MAARS_API_CONCURRENCY`）。

Execute -> Verify -> (pass | retry | redecompose) 是原子周期，在 semaphore 内完成。

## 7. 代码位置

| 文件 | 职责 |
|---|---|
| `backend/pipeline/research.py` | ResearchStage -- 主循环 + 任务执行 |
| `backend/pipeline/decompose.py` | 通用递归分解引擎 |
| `backend/pipeline/stage.py` | Stage 基类 + `_stream_llm` |
| `backend/pipeline/prompts_en.py` | EN prompts + builder 函数 |
| `backend/pipeline/prompts_zh.py` | ZH prompts |
| `backend/agno/tools/docker_exec.py` | code_execute + list_artifacts |
| `backend/agno/tools/db.py` | list_tasks + read_task_output + read_refined_idea + read_plan_tree |
