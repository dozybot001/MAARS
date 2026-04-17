# MAARS — Video Script (~4 min)

> 每行末尾 `·` = 按一次空格。`· ↓` = 按完页面会滚动或高亮切换。

---

Welcome to MAARS — Multi-Agent Automated Research System. `·`\
You give it a research idea. You get back a paper — with real experiments, real code, real figures. `·`\
Not a summary. Not a template. A complete research artifact, generated from scratch by a pipeline of collaborating LLM agents. `· ↓ scroll → Pipeline`

---

MAARS runs three stages: Refine, Research, and Write. `·`\
Each stage has a stable input-output boundary — the runtime orchestrates control flow and persistence; agents handle the open-ended intellectual work. `· ↓ highlight Refine`

---

Refine is where the raw idea gets sharpened into a structured research proposal. `·`\
Explorer surveys the literature — ArXiv, Wikipedia, web search — then drafts a scoped proposal with a clear research direction. `·`\
Critic reviews it, surfacing gaps and ambiguities. They iterate under the IterationState pattern until the critic has nothing left to flag. `· ↓ highlight Research`

---

Research is the core engine — where agents actually run experiments and produce results. `·`\
Calibrate runs once: a single LLM call that defines what an atomic task should look like for this specific problem. That definition anchors every decomposition prompt. `·`\
Strategy drafts a research plan and sets a scoring direction. Decompose splits it into a dependency DAG — sibling judges run in parallel, one failing branch never stalls the rest. `·`\
Execute runs tasks in topological batches. Key design: one persistent Docker container stays alive for the whole session — installed packages survive across tasks, eliminating roughly 190 seconds of overhead per task. `·`\
Verify reviews each result: pass, retry, or redecompose. Redecompose forwards prior partial outputs to the new subtasks — the system refines rather than restarts. `·`\
Finally, Evaluate. It's deliberately biased toward stopping — only triggering another Strategy round when it finds a critical gap. `· ↓ highlight Write`

---

Write takes everything Research produced and turns it into a paper. `·`\
Writer drafts, Reviewer critiques — same IterationState pattern as Refine, until zero issues remain. `·`\
A final Polish sub-step refines the prose and appends a deterministic metadata appendix — tokens, timings, model versions, a full file manifest. `· ↓ scroll → Architecture`

---

Under the hood, five layers — from a FastAPI server with SSE streaming, down through the orchestrator and stage layer, to agents running on Agno with Gemini, and a file-based session DB at the base. `·`\
Every run is just a directory: proposals, task outputs, the polished paper, and a reproduce bundle with a Dockerfile. No hidden state. `· ↓ scroll → Showcase / Lorenz`

---

Let's look at real outputs. First: a one-line prompt — solve the Lorenz system and produce four chaos figures. `·`\
Out came a complete paper: derivations, code, and four publication-quality plots — 3D trajectory, bifurcation diagram, Lyapunov curve, stability heatmap. `·`\
Eleven minutes. 347k tokens. `· ↓ scroll → Showcase / CIFAR`

---

Second case, harder. Does legitimate transfer learning weaken a backdoor watermark in a neural network? `·`\
MAARS designed the protocol, poisoned a CIFAR-10 model, ran two fine-tuning strategies on CIFAR-100, and delivered the comparative figures that went into the paper. `·`\
Three hours. 2.47 million tokens. `· ↓ scroll → Demo video`

---

Here is a live screen recording of a complete MAARS run — the full pipeline from idea to paper. `·`\
I'll scrub through so you can see the timeline. `·`\
*[拖动进度条展示]* `· ↓ scroll → Docs`

---

Full documentation is on the website. `·`\
Architecture — five layers, SSE protocol, storage layout, stage inheritance. `·` *(自动跳转)*\
Refine & Write — IterationState pattern, how the Primary ↔ Reviewer loop converges. `·` *(自动跳转)*\
Research — every phase from Calibrate through Evaluate, with code references. `·` *(自动跳转)*

---

One command to get started: bash start.sh — sets up the environment, builds the Docker image, serves on localhost:8000. `·`\
Paste your idea, or a Kaggle competition URL, and press Enter. `·`\
MAARS is open source at dozybot001/MAARS. Thanks for watching. `·`

---

## 快速启动

```bash
cd /path/to/MAARS/site
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080/?tp=1
```

## 按键

| 键 | 动作 |
|----|------|
| `Space` | 下一行（`· ↓` 处自动滚动或切换高亮） |
| `←` | 上一行 |
| `H` | 隐藏 / 显示字幕条 |
