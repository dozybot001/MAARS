"""Polish stage: single-pass paper refinement + deterministic metadata appendix."""

import time

from backend.pipeline.stage import Stage


class PolishStage(Stage):

    def __init__(self, name: str = "polish", model=None, tools=None, db=None):
        super().__init__(name=name, db=db)
        self._model = model
        self._tools = tools or []

    async def _execute(self) -> str:
        paper = self.db.get_document("paper") if self.db else ""
        if not paper:
            raise RuntimeError("No paper.md found — run the Write stage first.")

        # 1. LLM polish pass
        self._current_phase = "polish"
        from backend.team.prompts import POLISH_SYSTEM
        polished = await self._stream_llm(
            self._model, self._tools, POLISH_SYSTEM,
            self._build_input(paper),
            call_id="Polish", content_level=3,
            label=True, label_level=2,
        )

        # 2. Deterministic metadata appendix
        self._current_phase = "metadata"
        appendix = self._build_metadata_appendix()
        self._send(chunk={"text": appendix, "call_id": "Metadata", "level": 3})

        final = polished.rstrip() + "\n\n" + appendix
        if self.db:
            self.db.save_paper_final(final)
        return final

    # ------------------------------------------------------------------
    # Input builder
    # ------------------------------------------------------------------

    def _build_input(self, paper: str) -> str:
        from backend.config import settings
        parts: list[str] = []
        zh = settings.is_chinese()

        if zh:
            parts.append("## 待打磨论文\n")
            parts.append(paper)
            parts.append("\n## 规范化实验摘要（事实锚点，不可篡改）\n")
        else:
            parts.append("## Paper to Polish\n")
            parts.append(paper)
            parts.append("\n## Canonical Results Summary (factual anchor — do not alter)\n")

        if self.db:
            summary = self.db.get_results_summary()
            if summary:
                parts.append(summary)

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Deterministic metadata appendix
    # ------------------------------------------------------------------

    def _build_metadata_appendix(self) -> str:
        from backend.config import settings
        zh = settings.is_chinese()

        meta = self.db.get_meta() if self.db else {}
        research_id = self.db.research_id if self.db else "unknown"

        # --- Duration ---
        duration_str = self._calc_duration()

        # --- Task & artifact stats ---
        task_count = 0
        artifact_count = 0
        if self.db:
            plan_list = self.db.get_plan_list()
            task_count = sum(1 for t in plan_list if t.get("summary"))
            artifact_count = self._count_artifacts()

        # --- Token stats ---
        tokens_in = meta.get("tokens_input", 0)
        tokens_out = meta.get("tokens_output", 0)
        tokens_total = meta.get("tokens_total", 0)

        # --- Model config ---
        main_model = settings.google_model
        refine_model = settings.refine_model or main_model
        research_model = settings.research_model or main_model
        write_model = settings.write_model or main_model

        if zh:
            return self._render_appendix_zh(
                research_id=research_id,
                duration=duration_str,
                task_count=task_count,
                artifact_count=artifact_count,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                tokens_total=tokens_total,
                main_model=main_model,
                refine_model=refine_model,
                research_model=research_model,
                write_model=write_model,
                settings=settings,
            )
        return self._render_appendix_en(
            research_id=research_id,
            duration=duration_str,
            task_count=task_count,
            artifact_count=artifact_count,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            tokens_total=tokens_total,
            main_model=main_model,
            refine_model=refine_model,
            research_model=research_model,
            write_model=write_model,
            settings=settings,
        )

    def _calc_duration(self) -> str:
        if not self.db:
            return "N/A"
        log_entries = self.db.get_execution_log()
        if not log_entries:
            return "N/A"
        first_ts = log_entries[0].get("ts", 0)
        last_ts = log_entries[-1].get("ts", 0)
        if not first_ts or not last_ts:
            return "N/A"
        minutes = (last_ts - first_ts) / 60
        return f"{minutes:.1f} min"

    def _count_artifacts(self) -> int:
        if not self.db:
            return 0
        artifacts_dir = self.db.get_artifacts_dir()
        if not artifacts_dir.exists():
            return 0
        return sum(1 for _ in artifacts_dir.rglob("*") if _.is_file())

    # ------------------------------------------------------------------
    # Appendix renderers
    # ------------------------------------------------------------------

    @staticmethod
    def _render_appendix_zh(*, research_id, duration, task_count, artifact_count,
                            tokens_in, tokens_out, tokens_total,
                            main_model, refine_model, research_model, write_model,
                            settings) -> str:
        return f"""---

## 附录：MAARS 执行报告

**Run ID** `{research_id}`

### 运行配置

| 配置项 | 值 |
|--------|-----|
| 主模型 | `{main_model}` |
| Refine 模型 | `{refine_model}` |
| Research 模型 | `{research_model}` |
| Write 模型 | `{write_model}` |
| 输出语言 | `{settings.output_language}` |
| API 并发 | `{settings.api_concurrency}` |
| 研究迭代上限 | `{settings.research_max_iterations}` |
| 团队委托上限 | `{settings.team_max_delegations}` |

### 沙箱配置

| 配置项 | 值 |
|--------|-----|
| 镜像 | `{settings.docker_sandbox_image}` |
| 内存限制 | `{settings.docker_sandbox_memory}` |
| CPU 限制 | `{settings.docker_sandbox_cpu}` |
| 单次执行超时 | `{settings.docker_sandbox_timeout}s` |
| 会话超时 | `{settings.agent_session_timeout_seconds()}s` |
| 网络 | `{"启用" if settings.docker_sandbox_network else "禁用"}` |
| GPU | `{"启用" if settings.docker_sandbox_gpu else "禁用"}` |

### 运行统计

| 指标 | 值 |
|------|-----|
| 已完成任务 | `{task_count}` |
| 产物文件数 | `{artifact_count}` |
| 输入 token | `{tokens_in:,}` |
| 输出 token | `{tokens_out:,}` |
| 总 token | `{tokens_total:,}` |
| 总耗时 | `{duration}` |

### 产物清单

| 文件 | 说明 |
|------|------|
| `paper_final.md` | 最终论文（含本附录） |
| `paper.md` | Write 阶段初稿 |
| `results_summary.json` | 规范化实验摘要 |
| `results_summary.md` | 实验摘要（可读版） |
| `plan_tree.json` | 任务分解树 |
| `meta.json` | 运行元数据 |
"""

    @staticmethod
    def _render_appendix_en(*, research_id, duration, task_count, artifact_count,
                            tokens_in, tokens_out, tokens_total,
                            main_model, refine_model, research_model, write_model,
                            settings) -> str:
        return f"""---

## Appendix: MAARS Execution Report

**Run ID** `{research_id}`

### Configuration

| Setting | Value |
|---------|-------|
| Main model | `{main_model}` |
| Refine model | `{refine_model}` |
| Research model | `{research_model}` |
| Write model | `{write_model}` |
| Output language | `{settings.output_language}` |
| API concurrency | `{settings.api_concurrency}` |
| Research iteration limit | `{settings.research_max_iterations}` |
| Team delegation limit | `{settings.team_max_delegations}` |

### Sandbox

| Setting | Value |
|---------|-------|
| Image | `{settings.docker_sandbox_image}` |
| Memory limit | `{settings.docker_sandbox_memory}` |
| CPU limit | `{settings.docker_sandbox_cpu}` |
| Execution timeout | `{settings.docker_sandbox_timeout}s` |
| Session timeout | `{settings.agent_session_timeout_seconds()}s` |
| Network | `{"enabled" if settings.docker_sandbox_network else "disabled"}` |
| GPU | `{"enabled" if settings.docker_sandbox_gpu else "disabled"}` |

### Run Statistics

| Metric | Value |
|--------|-------|
| Completed tasks | `{task_count}` |
| Artifact files | `{artifact_count}` |
| Input tokens | `{tokens_in:,}` |
| Output tokens | `{tokens_out:,}` |
| Total tokens | `{tokens_total:,}` |
| Total duration | `{duration}` |

### File Manifest

| File | Description |
|------|-------------|
| `paper_final.md` | Final paper (with this appendix) |
| `paper.md` | Write stage draft |
| `results_summary.json` | Canonical results summary |
| `results_summary.md` | Results summary (readable) |
| `plan_tree.json` | Task decomposition tree |
| `meta.json` | Run metadata |
"""
