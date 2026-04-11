# MAARS CLI 命令参考

> 完整的命令清单、参数详解、示例和常见问题。快速概览见 [README.md](../README.md#使用)。

## 总览

| 命令 | 类别 | 用途 |
|---|---|---|
| `maars refine` | **graph** | Refine graph（Explorer ↔ Critic 对抗循环） |
| `maars write` | **graph** | Write graph（Writer ↔ Reviewer 对抗循环） |
| `maars hello` | diagnostic | CLI wiring smoke test |
| `maars sanity` | debug | 单次 chat model invoke，验证 API + key |
| `maars draft` | debug | 单次 Explorer 调用，不迭代 |
| `maars critique` | debug | 单次 Critic 调用，不迭代 |

**快速启动**：

```bash
uv run maars --help            # 看所有命令
uv run maars refine --help     # 看某个命令的完整参数
uv run maars hello             # 最轻量的自检
```

---

## Graph 命令（M1 / M2 的主要入口）

### `maars refine`

运行完整的 Refine graph——Explorer 起草研究提案，Critic 审查，迭代直到 `passed=True` 或达到 MAX_ROUND。

#### Synopsis

```
uv run maars refine [RAW_IDEA] [OPTIONS]
uv run maars refine --from-file <PATH> [OPTIONS]
```

#### 参数

| 参数 | 类型 | 必需 | 默认 | 说明 |
|---|---|---|---|---|
| `RAW_IDEA` | positional | 二选一 | `""` | 研究想法字符串（与 `--from-file` 二选一） |
| `--from-file`, `-f` | Path | 二选一 | — | 从 markdown 文件读取 idea（长 idea 或含特殊字符推荐） |
| `--thread` | str | 否 | `default` | Checkpoint + resume 的 thread id |
| `--fresh` | bool | 否 | `false` | 忽略同 thread 已有 checkpoint，自动生成带随机后缀的新 thread |

#### 示例

```bash
# 最简：短 idea 直接传
uv run maars refine "研究大模型推理"

# 带自定义 thread id（推荐，避免 default 冲突）
uv run maars refine "研究多模态推理" --thread multimodal1

# 从文件读长 idea（几段话 + markdown + 特殊字符都 ok）
uv run maars refine --from-file examples/test_ideas/speculative_decoding.md --thread spec1

# Resume 同 thread id（如果 checkpoint 存在会自动从上次中断处继续）
uv run maars refine --from-file my_idea.md --thread spec1

# 已有同 thread 的 state 但想重跑：加 --fresh，系统自动后缀 (thread 变成 spec1-abc123)
uv run maars refine --from-file my_idea.md --thread spec1 --fresh

# 放宽 MAX_ROUND 让 Critic 有更多轮收敛（env var）
MAARS_REFINE_MAX_ROUND=8 uv run maars refine "..." --thread long-run
```

#### 输出

1. **Streaming events**（实时）：

   ```
   Starting thread spec1
   ────────────────────────────────
   -> explorer running...
   ok explorer round 1 — draft generated (2047 chars)
   -> critic running...
   ok critic — 5 issues, passed=False
   -> explorer running...
   ok explorer round 2 — draft generated (2340 chars)
   ok critic — 3 issues, passed=False, resolved+5
   ...
   ```

2. **Final Rich Panel**：完整的 refined draft（不截断）
3. **Remaining issues**：按 severity 分色（red = blocker / yellow = major / dim = minor）
4. **文件落盘**：最终 draft 保存到 `data/ideas/{thread_id}.md`
5. **Resume hint**：最后一行打印继续这个 thread 的命令

#### 典型迭代模式

```
Round 1: 6 issues (0 resolved, 6 new)          # 首轮发现基线
Round 2: 3 issues, resolved+6                  # 前 6 全部修好，新挑 3 个
Round 3: 3 issues, resolved+3
Round 4: 3 issues, resolved+3
Round 5: 3 issues, resolved+3                  # MAX_ROUND 触发 END
```

如果中间某轮 `passed=True` 会提前终止。新架构下 `resolved` 数量通常接近 prior issues 数量（Explorer 真的在修东西），issue count 稳定在 3-5 之间（Critic 越挑越细）。

---

### `maars write`

运行完整的 Write graph——Writer 根据 refined idea + experiment artifacts 起草论文，Reviewer 审查，迭代直到 `passed=True` 或达到 MAX_ROUND。

#### Synopsis

```
uv run maars write <IDEA_PATH> <ARTIFACTS_DIR> [OPTIONS]
```

#### 参数

| 参数 | 类型 | 必需 | 默认 | 说明 |
|---|---|---|---|---|
| `IDEA_PATH` | positional Path | ✅ | — | refined idea 的 markdown 文件路径 |
| `ARTIFACTS_DIR` | positional Path | ✅ | — | artifacts 目录（递归读取所有 `*.md` 作为 experiment context） |
| `--thread` | str | 否 | `default-write` | Checkpoint + resume 的 thread id |
| `--fresh` | bool | 否 | `false` | 忽略同 thread 已有 checkpoint |

#### 示例

```bash
# 用自带的 fake artifacts 测试（PRM vs Best-of-N on GSM8K 的假数据）
uv run maars write examples/fake_artifacts/refined_idea.md examples/fake_artifacts --thread w1

# 用 maars refine 产出的 idea 作为 write 的 input（手动 pipeline）
uv run maars write data/ideas/spec1.md my_experiments/ --thread spec1-paper

# Resume
uv run maars write my_idea.md my_experiments/ --thread spec1-paper
```

#### 输出

1. **Streaming events**：每轮 Writer / Reviewer 状态
2. **Preview Panel**：前 1200 字符的 Panel（完整版看落盘文件）
3. **Paper 落盘**：`data/papers/{thread_id}.md`
4. **Remaining issues**：按 severity 分色

#### 注意

- `ARTIFACTS_DIR` 下所有 `.md` 文件（递归）会被读进 Writer 的 context——文件越多 prompt 越长，API 成本越高
- Refined idea 文件可以是 `maars refine` 产出的（`data/ideas/{thread}.md`），也可以是你手写的
- Paper 常常很长（5k+ chars），Panel 只显示 preview，完整内容看落盘文件

---

## Debug / Diagnostic 命令

这些命令主要用于开发和调试，**不是正常使用流程的一部分**。

### `maars hello`

最轻量的 CLI 自检，只打印 `"MAARS CLI ready."`。验证 typer 配置、Python import、packaging 都 OK。

```bash
uv run maars hello
# MAARS CLI ready. (Step 1 of M1)
```

不打 API，0 花费，瞬间返回。

### `maars sanity`

单次调用 chat model，验证 `GOOGLE_API_KEY` 有效且 `MAARS_CHAT_MODEL` 被 Gemini 识别。

```bash
uv run maars sanity
# Model: gemini-3-flash-preview
# Response: hello from model
```

打 1 次 Gemini API（< $0.001）。**遇到 API / 配置问题第一步就跑这个**。

### `maars draft <raw_idea>`

**只跑一次 Explorer**，不进入 Refine 循环。拿到一个基于 idea 的 draft 就结束。用于快速看 Explorer 单次的 output 长什么样。

```bash
uv run maars draft "研究大模型推理"
```

打 1 次 Gemini API + 内置 google_search grounding。约 10-20 秒，< $0.01。

### `maars critique <draft>`

**只跑一次 Critic**，不进入 Refine 循环。对一个 draft 字符串给出结构化的 issues + passed。

```bash
uv run maars critique "我想在 GSM8K 上研究 CoT 效果"
```

打 1 次 Gemini API（structured output）。约 5-10 秒，< $0.005。

**注意**：如果 draft 很长或含换行/markdown/数学符号，shell 转义会很痛苦。直接用 `maars refine` 走完整流程更顺。

---

## 环境变量

所有 env 变量都可以：

- 写在 `.env` 文件里（推荐长期配置）
- 或 inline 传给单次命令：`VAR=val uv run maars ...`

| 变量 | 默认 | 说明 |
|---|---|---|
| `GOOGLE_API_KEY` | — | **必填**，Gemini API key |
| `MAARS_CHAT_MODEL` | `gemini-3-flash-preview` | Gemini 模型 ID（`gemini-3-pro` / `gemini-2.5-pro` 等） |
| `MAARS_REFINE_MAX_ROUND` | `5` | Refine 最大迭代轮次 |
| `MAARS_WRITE_MAX_ROUND` | `5` | Write 最大迭代轮次 |

### Inline 使用

```bash
# 单次放宽 MAX_ROUND
MAARS_REFINE_MAX_ROUND=10 uv run maars refine "..." --thread long

# 单次切换到 pro 模型（更贵更强）
MAARS_CHAT_MODEL=gemini-3-pro uv run maars refine "..."

# 同时设多个
MAARS_CHAT_MODEL=gemini-3-pro MAARS_REFINE_MAX_ROUND=8 uv run maars refine "..."
```

### 写 `.env`

```bash
# .env
GOOGLE_API_KEY=sk-your-key-here
MAARS_REFINE_MAX_ROUND=8
MAARS_CHAT_MODEL=gemini-3-flash-preview
```

`.env` 在 `.gitignore` 里，不会被 commit。

---

## 文件位置约定

| 路径 | 内容 | git 跟踪 |
|---|---|---|
| `data/checkpoints.db` | LangGraph state checkpoints（所有 thread） | ❌ gitignored |
| `data/ideas/{thread_id}.md` | `maars refine` final draft 落盘 | ❌ gitignored |
| `data/papers/{thread_id}.md` | `maars write` final paper 落盘 | ❌ gitignored |
| `examples/fake_artifacts/` | 自带的 Write graph 测试 fixture | ✅ tracked |
| `examples/test_ideas/` | 自带的 Refine graph 测试 idea | ✅ tracked |

---

## 常见命令 Pattern

### 1. 快速测试 Refine

```bash
# 1. 先 sanity check API
uv run maars sanity

# 2. 跑 refine（用自带的 test idea）
uv run maars refine --from-file examples/test_ideas/speculative_decoding.md --thread test1

# 3. 看完整 draft
cat data/ideas/test1.md
```

### 2. 跑多个 idea 对比

```bash
uv run maars refine "idea A" --thread ideaA
uv run maars refine "idea B" --thread ideaB
uv run maars refine "idea C" --thread ideaC

ls data/ideas/
# ideaA.md  ideaB.md  ideaC.md  ...
```

### 3. Refine → Write 手动 pipeline

```bash
# 1. 先 refine 想法
uv run maars refine --from-file my_idea.md --thread proj1

# 2. 手动准备 artifacts（模拟实验结果 markdown）
mkdir -p my_artifacts
cat > my_artifacts/results.md <<'EOF'
# Experiment Results
## Setup
...
EOF

# 3. 用 refine 产出的 idea 作为 write 的 input
uv run maars write data/ideas/proj1.md my_artifacts/ --thread proj1-paper

# 4. 看 paper
cat data/papers/proj1-paper.md
```

### 4. 中断 → Resume

```bash
# 跑到一半 Ctrl-C
uv run maars refine "..." --thread long1
^C

# 同 thread id 再跑一次，会从最后一个 checkpoint 继续
uv run maars refine "..." --thread long1
# "Resuming thread long1 from round 3" → 继续从 round 4
```

### 5. 新实验，但名字想用已用过的 thread id

```bash
# 方案 A: 用不同的 thread id
uv run maars refine "new idea" --thread long1-v2

# 方案 B: --fresh 自动生成带后缀的 thread id
uv run maars refine "new idea" --thread long1 --fresh
# "--fresh: starting new thread long1-abc123 (keeping long1 intact)"
```

### 6. 清空所有 state 从头开始

```bash
# 注意：这会删掉所有 thread 的 checkpoint，但 data/ideas/*.md 保留
rm data/checkpoints.db
```

---

## FAQ / 常见问题

**Q: 我跑了一次 `maars refine "..."`，第二次再跑同样的命令看到 "Resuming thread default from round 5" 然后立即结束**

A: 默认 `--thread` 是 `"default"`，第一次跑已经把 state 存到 checkpoint 里了。第二次没改 thread id → LangGraph 自动 resume + `should_continue` 返回 END（因为 round ≥ MAX 或 passed=True）。

解决：

- 加 `--thread <new_id>` 用新 thread
- 或加 `--fresh` 自动生成带后缀的新 thread id

---

**Q: `Error: file not found: my_idea.md`**

A: `--from-file` 路径是相对**当前工作目录**的。

- 确认 `pwd` 是 MAARS 根目录
- 确认文件实际存在：`ls my_idea.md`
- 如果文件在别处，用绝对路径或相对路径：`--from-file ~/Desktop/my_idea.md`

---

**Q: 怎么清理某个 thread 的 state（但保留其他 thread）？**

A: 目前没有单独的 per-thread 清理命令。可以：

- 用不同的 thread id 开新一次（最简单）
- 或 `rm data/checkpoints.db` 清空**所有** thread（`data/ideas/*.md` 不受影响）
- 或写个 SQL: `sqlite3 data/checkpoints.db "DELETE FROM checkpoints WHERE thread_id='xxx'"`（进阶）

---

**Q: 跑一次 Refine 大概多少 API 花费？**

A: 每轮 Explorer + Critic 两次 Gemini API 调用：

- Explorer：带 `google_search` grounding，约 $0.003-0.005
- Critic：structured output，约 $0.001-0.002
- 每轮合计 ~$0.005-0.007
- 5 轮（MAX_ROUND default）：**约 $0.03-0.04 一次完整 Refine**

Write 稍贵一点（paper 更长）：约 $0.05-0.10 一次完整 run。

---

**Q: `passed=False` 到 MAX_ROUND 是 bug 吗？**

A: 不是。Critic 设计得严格，每轮都能找到新的 deeper issue。`passed=True` 需要 "0 blocker + ≤1 major"，对复杂 idea 来说 5 轮可能不够。

如果想让 Refine 更容易收敛：

- 放宽 `MAARS_REFINE_MAX_ROUND=8` 或 `10`
- 或提供更具体的 initial idea（已经包含 baseline、dataset、metric 等）

如果 draft 本身已经很好，`passed=False` 不影响使用——最终 draft 还是会保存到 `data/ideas/{thread}.md`。

---

**Q: `passed=True` 时会马上停吗？**

A: 是。`should_continue` 在 Critic node 之后看 `state.passed`，如果 `True` 直接返回 `END`，graph 结束。所以如果第 2 轮就 passed，只会跑 2 × (Explorer + Critic) = 4 次 LLM 调用。

---

**Q: 我的 idea 用英文写可以吗？**

A: 可以。prompt 是中文的（Explorer/Critic 都是中文角色），但 LLM 处理双语没问题。Explorer 的 draft 可能混合中英（比如数学公式和 model id 保持英文），这是正常的。

---

## 调试 checklist

遇到问题时按顺序排查：

1. **`uv run maars hello`** — CLI 能启动吗？（验证 typer 配置、Python import、packaging）
2. **`uv run maars sanity`** — API key / 网络 / 模型 ID 正常吗？
3. **`ls data/`** — `checkpoints.db` 存在吗？`ideas/papers` 目录有什么？
4. **`uv run maars refine --help`** — 参数签名对吗？help 打印是否和你的命令对得上？
5. **看 traceback** — 错误在 Python / Pydantic / LangGraph / Gemini API 的哪一层？
6. **`rm data/checkpoints.db` + 换 thread id** — state 污染可能导致奇怪的 resume 行为，清掉最彻底

---

## 相关文档

- [README.md](../README.md) — 项目概览和快速开始
- [docs/concept.md](concept.md) — 核心思想
- [docs/architecture.md](architecture.md) — 技术栈和模块设计
- [docs/graph.md](graph.md) — 每个 graph 的 State / Node / Edge 定义
- [docs/roadmap.md](roadmap.md) — 里程碑和"不做什么"清单
