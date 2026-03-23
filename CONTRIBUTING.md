# Contributing | 贡献指南

[中文](#中文) | [English](#english)

## English

Thank you for your interest in MAARS! Here's how to get started.

### Development Setup

```bash
git clone https://github.com/dozybot001/MAARS.git
cd MAARS
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Run in mock mode (no API key needed):
```bash
uvicorn backend.main:app --reload
```

### Project Structure

```
backend/
├── pipeline/    # Core framework (BaseStage, orchestrator) — mode-agnostic
├── llm/         # LLMClient interface
├── mock/        # Mock mode implementation
├── gemini/      # Gemini mode implementation
├── agent/       # Agent mode implementation (Google ADK)
├── routes/      # FastAPI HTTP/SSE endpoints
└── db.py        # File-based research storage

frontend/
├── index.html   # Single page
├── css/         # Modular CSS (variables, layout, workspace, etc.)
└── js/          # ES modules (events, api, log-viewer, process-viewer, etc.)
```

### Key Principles

1. **Pipeline layer is mode-agnostic.** `pipeline/` must never import from `mock/`, `gemini/`, or `agent/`.
2. **Unified streaming model.** All LLM calls use `call_id`-tagged chunks.
3. **String in, string out.** Stages communicate through `stage.output`.
4. **No build step for frontend.** Vanilla JS/CSS only.

### How to Contribute

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/your-feature`
3. **Make changes** following the principles above
4. **Test** with mock mode: `MAARS_LLM_MODE=mock uvicorn backend.main:app --reload`
5. **Submit** a Pull Request with a clear description

### Adding a New Mode

Create a new directory under `backend/` (e.g., `backend/openai/`):
1. Implement `LLMClient` interface (see `llm/client.py`)
2. Create `create_xxx_stages()` assembly function
3. Add mode to `main.py` dispatch

### Adding Tools for Agent Mode

Add to `backend/agent/tools/`:
- Shared tools: `tools/shared/`
- Stage-specific tools: `tools/<stage_name>/`

---

## 中文

感谢你对 MAARS 的关注！以下是参与方式。

### 开发环境

```bash
git clone https://github.com/dozybot001/MAARS.git
cd MAARS
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

使用 mock 模式运行（无需 API key）：
```bash
uvicorn backend.main:app --reload
```

### 核心原则

1. **Pipeline 层与模式无关。** `pipeline/` 绝不能导入 `mock/`、`gemini/` 或 `agent/`。
2. **统一流式模型。** 所有 LLM 调用使用 `call_id` 标记的 chunk。
3. **字符串进，字符串出。** 阶段间通过 `stage.output` 通信。
4. **前端零构建步骤。** 仅使用原生 JS/CSS。

### 如何贡献

1. **Fork** 仓库
2. **创建**特性分支：`git checkout -b feature/your-feature`
3. **修改**代码，遵循以上原则
4. **测试**：`MAARS_LLM_MODE=mock uvicorn backend.main:app --reload`
5. **提交** Pull Request，附上清晰的描述

### 添加新模式

在 `backend/` 下创建新目录，实现 `LLMClient` 接口，编写组装函数，在 `main.py` 中添加分发逻辑。

### 添加 Agent 工具

共享工具放入 `backend/agent/tools/shared/`，阶段专有工具放入 `backend/agent/tools/<stage_name>/`。
