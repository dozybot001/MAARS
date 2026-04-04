# MAARS

中文 | [English](README.md)

**多智能体自动化研究系统** — 从研究想法或 Kaggle 比赛链接，到结构化研究产物与 `paper.md` 的端到端编排。

## 功能

- **精炼（Refine）**：将输入整理为可执行研究方案（`refined_idea.md`）
- **研究（Research）**：校准 → 策略 → 分解 → 执行 ⇄ 验证 → 评估，支持多轮迭代改进
- **写作（Write）**：将研究产物整理为 `paper.md`
- **Kaggle 模式**：粘贴比赛链接，自动提取 ID、下载数据到 `MAARS_DATASET_DIR`，跳过精炼阶段
- **沙箱**：所有代码在 Docker 容器中执行

## 快速开始

**环境：** Python 3.10+，Docker 已运行

```bash
git clone https://github.com/dozybot001/MAARS.git && cd MAARS
bash start.sh
```

脚本会创建 venv、安装依赖、首次运行自动生成 `.env`、构建沙箱镜像，并在 `http://localhost:8000` 启动服务。

## 配置

变量均带 `MAARS_` 前缀，配置于 `.env`（首次 `start.sh` 时自动生成）。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MAARS_GOOGLE_API_KEY` | — | **必填。** Gemini API 密钥。 |
| `MAARS_GOOGLE_MODEL` | `gemini-3-flash-preview` | 传给 Agno 的模型 id。 |
| `MAARS_API_CONCURRENCY` | `1` | LLM 并发上限。 |
| `MAARS_OUTPUT_LANGUAGE` | `Chinese` | 提示词/输出语言包。 |
| `MAARS_RESEARCH_MAX_ITERATIONS` | `3` | 最大评估轮数。若 Evaluate 不再输出 `strategy_update` 会提前结束。 |
| `MAARS_KAGGLE_API_TOKEN` | — | 可选；也可用 `~/.kaggle/kaggle.json`。 |
| `MAARS_DATASET_DIR` | `data/` | Research 沙箱挂载的数据集目录。 |
| `MAARS_DOCKER_SANDBOX_IMAGE` | `maars-sandbox:latest` | 代码执行使用的 Docker 镜像。 |
| `MAARS_DOCKER_SANDBOX_TIMEOUT` | `600` | 单容器超时（秒）。 |
| `MAARS_DOCKER_SANDBOX_MEMORY` | `4g` | 内存上限（如 `512m`、`4g`）。 |
| `MAARS_DOCKER_SANDBOX_CPU` | `1.0` | CPU 配额。 |
| `MAARS_DOCKER_SANDBOX_NETWORK` | `true` | 沙箱内是否联网。 |
| `MAARS_SERVER_PORT` | `8000` | 服务端口（仅 `start.sh` 使用）。 |

## 文档

| 文档 | 内容 |
|------|------|
| [架构设计](docs/CN/architecture.md) | 系统设计、Research 环节、SSE、存储结构 |

## 社区

[贡献指南](.github/CONTRIBUTING.md) · [行为准则](.github/CODE_OF_CONDUCT.md) · [安全策略](.github/SECURITY.md)

## 许可证

MIT
