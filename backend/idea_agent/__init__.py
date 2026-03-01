"""
Idea Agent - 从模糊 idea 收集 arXiv 文献。
"""

from typing import Optional

from . import arxiv
from .llm import extract_keywords, extract_keywords_stream
from .llm.executor import OnThinkingCallback  # 统一 on_thinking 签名


async def collect_literature(
    idea: str,
    api_config: dict,
    limit: int = 10,
    on_thinking: Optional[OnThinkingCallback] = None,
) -> dict:
    """
    根据模糊 idea 收集 arXiv 文献。

    流程：LLM 提取关键词 -> 拼接为 arXiv 查询 -> 检索并解析。

    Args:
        idea: 用户输入的模糊研究想法
        api_config: API 配置
        limit: 返回文献数量上限
        on_thinking: 可选，流式时每收到 LLM token 调用，用于 Thinking 区域展示

    Returns:
        {keywords: [...], papers: [...]}
    """
    if on_thinking is not None:
        keywords = await extract_keywords_stream(idea, api_config, on_chunk=on_thinking)
    else:
        keywords = await extract_keywords(idea, api_config)
    if not keywords:
        keywords = ["research"]
    query = "+".join(str(k).replace(" ", "+") for k in keywords)[:100]
    if not query:
        query = "research"
    papers = await arxiv.search_arxiv(query, limit=limit)
    return {"keywords": keywords, "papers": papers}
