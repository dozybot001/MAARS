# 贡献指南

中文 | [English](CONTRIBUTING.md)

[项目说明](README_CN.md) | [行为准则](CODE_OF_CONDUCT_CN.md) | [安全策略](SECURITY_CN.md)

感谢你对 MAARS 的关注！下面是参与本项目的方式。

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

### 项目结构

```text
backend/
├── pipeline/    # 核心框架（BaseStage、orchestrator），与模式无关
├── llm/         # LLMClient 接口
├── mock/        # Mock 模式实现
├── gemini/      # Gemini 模式实现
├── agent/       # Agent 模式实现（Google ADK）
├── routes/      # FastAPI HTTP / SSE 接口
└── db.py        # 基于文件的研究结果存储

frontend/
├── index.html   # 单页入口
├── css/         # 模块化 CSS（变量、布局、工作区等）
└── js/          # ES modules（events、api、log-viewer、process-viewer 等）
```

### 核心原则

1. **Pipeline 层与模式无关。** `pipeline/` 绝不能导入 `mock/`、`gemini/` 或 `agent/`。
2. **统一流式模型。** 所有 LLM 调用都使用带 `call_id` 的 chunk。
3. **字符串进，字符串出。** 阶段之间通过 `stage.output` 通信。
4. **前端零构建步骤。** 仅使用原生 JS / CSS。

### 如何贡献

1. **Fork** 仓库
2. **创建**特性分支：`git checkout -b feature/your-feature`
3. **修改**代码，并遵循以上原则
4. **测试**：`MAARS_LLM_MODE=mock uvicorn backend.main:app --reload`
5. **提交** Pull Request，并附上清晰说明

### 添加新模式

在 `backend/` 下创建新目录（例如 `backend/openai/`）：

1. 实现 `LLMClient` 接口（参考 `llm/client.py`）
2. 编写 `create_xxx_stages()` 组装函数
3. 在 `main.py` 中加入模式分发

### 添加 Agent 工具

添加到 `backend/agent/tools/`：

- 共享工具：`tools/shared/`
- 阶段专用工具：`tools/<stage_name>/`
