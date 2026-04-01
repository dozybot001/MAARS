# SSE 架构

## 设计原则

1. **统一事件格式**：`{stage, phase?, chunk?, status?, task_id?, error?}`
2. **有 chunk = 进行中**：SSE 携带流式文本 payload，低延迟渲染
3. **无 chunk = 结束信号**：后端已将结果写入 DB，前端通过 API 获取
4. **DB 为唯一数据源**：所有状态持久化到文件，刷新不丢失
5. **Pipeline 由首次出现驱动**：新 stage/phase 首次出现 → 结束上一阶段，点亮当前阶段
6. **不依赖事件顺序**：section 由第一个 chunk 按需创建，不依赖 state 事件

## 层级结构

```
层级    名称     示例                      设置者
──────────────────────────────────────────────────────────
  1     Stage    REFINE / RESEARCH        orchestrator
  2     Phase    Calibrate / Explorer     _current_phase / chunk label
  3     Call     Exec 1 / Judge 1         chunk label (level=3)
  4     Tool     Tool: search / Thinking  chunk label (level=4)
```

- **Stage**（3 个）：refine、research、write — 顶层流水线步骤
- **Phase**（5 个）：calibrate、strategy、decompose、execute、evaluate — research 内部子步骤
- **Call/Tool**：chunk 流中的渲染细节，无结构性意义

## 后端：事件发送方式

### `Stage._send(chunk?, **extra)`

所有 SSE 事件的唯一发送方法，自动附带 `stage` 和 `phase`。

```python
def _send(self, chunk=None, **extra):
    event = {"stage": self.name}
    if self._current_phase:
        event["phase"] = self._current_phase
    if chunk:
        event["chunk"] = chunk
        self.db.append_log(...)   # 持久化到 log.jsonl
    event.update(extra)           # status, task_id, error
    self._broadcast(event)
```

### 关键规则：先写 DB，再发结束信号

```python
# 正确
self.db.save_strategy(strategy)
self._send()                      # 前端 fetch → 数据已存在

# 错误
self._send()                      # 前端 fetch → 数据不存在！
self.db.save_strategy(strategy)
```

### decompose 与 execute 的对称设计

decompose 和 execute 是唯一两个"实时更新"的结构化数据，遵循相同模式：

```
decompose:
  首个 judge 完成 → save_tree → done signal → 前端首次渲染分解树
  后续 judge 完成 → save_tree → done signal → 前端重绘分解树（增量更新）

execute:
  任务列表生成 → save plan_list(status=pending) → done signal → 前端首次渲染执行列表
  每个 task 完成 → update_task_status → done signal → 前端重绘执行列表（状态更新）
```

## 前端：三个监听器，同一个事件

```
on('sse') → pipeline-ui    // 仅首次出现新 stage/phase 时触发
on('sse') → log-viewer     // 有 chunk → 渲染；section 按需创建
on('sse') → process-viewer // 无 chunk → fetch DB → 渲染结构化内容
```

Phase group key = chunk 的 `call_id`（如 "Calibrate"），确保 `currentPhaseName` 和 `phaseGroups` 同步。

结构化渲染函数在 async fetch 前捕获 `container = target()`，防止竞态条件。

## DB 存储结构

```
results/{session}/
  log.jsonl               # 流式 chunk，追加写入
  execution_log.jsonl     # Docker 代码执行记录
  plan_list.json          # 任务列表，含 status
  plan_tree.json          # 分解树，每个 judge 完成后更新
  meta.json               # phase、score、tokens
  refined_idea.md         # refine 阶段输出
  paper.md                # write 阶段输出
  calibration.md          # calibrate 阶段输出
  strategy.md             # strategy 阶段输出
  idea.md                 # 用户原始输入
  tasks/{id}.md           # 各任务输出
  artifacts/              # 生成文件
  evaluations/            # 每轮评估 JSON
  reproduce/              # Dockerfile + run.sh + compose
```

## 完整运行时间线

```
SSE                                              前端动作
────────────────────────────────────────────────────────────────────

{stage:"refine", chunk:{label, level:2, "Explorer"}}
                                                  首次 "refine" → pipeline 点亮 refine
                                                  2 级 label → 创建 Explorer fold
{stage:"refine", chunk:{text, level:3}}           在 Explorer fold 中追加文本
...
{stage:"refine"}                                  结束 → 查 refined_idea.md → 文档卡片

{stage:"research", phase:"calibrate", chunk:{label, level:2}}
                                                  首次 "calibrate" → pipeline：
                                                    refine 变绿，calibrate 点亮
{stage:"research", phase:"calibrate"}             结束 → 查 calibration.md → 文档卡片

{stage:"research", phase:"strategy", chunk:{label, level:2}}
                                                  首次 "strategy" → pipeline 点亮
{stage:"research", phase:"strategy"}              结束 → 查 strategy.md → 文档卡片

{stage:"research", phase:"decompose", chunk:{label, level:2}}
                                                  首次 "decompose" → pipeline 点亮
{stage:"research", phase:"decompose", chunk:{label, level:3, "Judge 1"}}
                                                  创建 Judge 1 fold
{stage:"research", phase:"decompose"}             首个 done signal → 查 plan_tree → 首次渲染分解树
...
{stage:"research", phase:"decompose"}             后续 done → 重绘分解树

{stage:"research", phase:"execute", chunk:{label, level:2, "Execute"}}
                                                  首次 "execute" → pipeline 点亮
{stage:"research", phase:"execute"}               首个 done signal → 查 plan_list → 首次渲染执行列表
{stage:"research", phase:"execute", status:"running", task_id:"1"}
                                                  任务 1 标记为 running
{stage:"research", phase:"execute", chunk:{label, level:3}, task_id:"1"}
                                                  创建 Exec 1 fold
{stage:"research", phase:"execute", task_id:"1"}  结束 → 查 plan_list → 任务 1 已完成

{stage:"research", phase:"evaluate", chunk:{...}} 首次 "evaluate" → pipeline 点亮
{stage:"research", phase:"evaluate"}              结束 → 查 meta → 分数指标

{stage:"write", chunk:{label, level:2, "Writer"}} 首次 "write" → pipeline 点亮
...
{stage:"write"}                                   结束 → 查 paper.md → 文档卡片
```
