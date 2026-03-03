"""
Paper Agent - 单轮 LLM 管道，根据 plan 与 task outputs 生成论文草稿。
当前仅集成 LLM 管道，Agent 模式（工具调用、多轮推理）待开发。
"""

from .runner import run_paper_agent

__all__ = ["run_paper_agent"]
