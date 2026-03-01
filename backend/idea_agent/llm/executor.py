"""
Idea Agent 单轮 LLM 实现 - 关键词提取。
与 Plan 对齐：Mock 模式依赖 test/mock-ai/refine.json，使用 mock_chat_completion 流式输出。
"""

import json
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional

import orjson

from shared.llm_client import chat_completion, merge_phase_config
from test.mock_stream import mock_chat_completion

# 与 Plan/Task 统一的 on_thinking 签名：(chunk, task_id, operation, schedule_info)
OnThinkingCallback = Callable[[str, Optional[str], Optional[str], Optional[dict]], None]

IDEA_DIR = Path(__file__).resolve().parent.parent
MOCK_AI_DIR = IDEA_DIR.parent / "test" / "mock-ai"
RESPONSE_TYPE = "refine"
MOCK_KEY = "_default"

_mock_cache: Dict[str, dict] = {}


def _get_mock_cached(response_type: str) -> dict:
    if response_type not in _mock_cache:
        path = MOCK_AI_DIR / f"{response_type}.json"
        try:
            _mock_cache[response_type] = orjson.loads(path.read_bytes())
        except (FileNotFoundError, orjson.JSONDecodeError):
            _mock_cache[response_type] = {}
    return _mock_cache[response_type]


def _load_mock_response(response_type: str, key: str) -> Optional[Dict]:
    """从 test/mock-ai/ 加载 mock，与 Plan 对齐。"""
    data = _get_mock_cached(response_type)
    entry = data.get(key) or data.get("_default")
    if not entry:
        return None
    content = entry.get("content")
    if isinstance(content, str):
        content_str = content
    else:
        content_str = orjson.dumps(content).decode("utf-8")
    return {"content": content_str, "reasoning": entry.get("reasoning", "")}


# LLM 提示词：用于 arXiv 检索，输出英文关键词
_SYSTEM_PROMPT = """You are a research assistant. Extract 3-5 concise keywords suitable for arXiv search from the user's fuzzy research idea.
Requirements:
- Keywords should be technical terms or domain nouns, no stop words (e.g. the, a, and)
- Output pure JSON only: {"keywords": ["keyword1", "keyword2", ...]}
- Output JSON only, no other content"""


def _parse_keywords_response(text: str) -> List[str]:
    """解析 LLM 返回的 JSON，提取 keywords 列表。"""
    cleaned = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if m:
        cleaned = m.group(1).strip()
    try:
        data = json.loads(cleaned)
        keywords = data.get("keywords")
        if isinstance(keywords, list):
            result = [str(k).strip() for k in keywords if k and str(k).strip()]
            return result[:10] if result else []
    except (json.JSONDecodeError, TypeError):
        pass
    return []


async def extract_keywords(idea: str, api_config: dict) -> List[str]:
    """
    从模糊 idea 中提取 arXiv 检索关键词。
    Mock 模式：从 test/mock-ai/refine.json 加载并解析。
    """
    if not idea or not isinstance(idea, str):
        return []
    idea = idea.strip()
    if not idea:
        return []

    use_mock = api_config.get("useMock", True)
    if use_mock:
        mock = _load_mock_response(RESPONSE_TYPE, MOCK_KEY)
        if not mock:
            raise ValueError(f"No mock data for {RESPONSE_TYPE}/{MOCK_KEY}")
        return _parse_keywords_response(mock["content"])

    cfg = merge_phase_config(api_config, "idea")
    ai_mode = api_config.get("aiMode", "llm")
    mode_cfg = api_config.get("modeConfig", {}).get(ai_mode, {})
    temperature = mode_cfg.get("ideaLlmTemperature")
    if temperature is not None:
        temperature = float(temperature)
    else:
        temperature = 0.3
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": idea},
    ]
    try:
        response = await chat_completion(
            messages,
            cfg,
            stream=False,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        text = response if isinstance(response, str) else str(response)
        return _parse_keywords_response(text)
    except Exception:
        return []


async def extract_keywords_stream(
    idea: str,
    api_config: dict,
    on_chunk: Optional[OnThinkingCallback] = None,
) -> List[str]:
    """
    流式从模糊 idea 中提取 arXiv 检索关键词。
    Mock 模式：从 test/mock-ai/refine.json 加载，通过 mock_chat_completion 流式输出 reasoning。
    """
    if not idea or not isinstance(idea, str):
        return []
    idea = idea.strip()
    if not idea:
        return []

    use_mock = api_config.get("useMock", True)
    if use_mock:
        mock = _load_mock_response(RESPONSE_TYPE, MOCK_KEY)
        if not mock:
            raise ValueError(f"No mock data for {RESPONSE_TYPE}/{MOCK_KEY}")
        stream = on_chunk is not None

        def stream_chunk(chunk: str):
            if on_chunk and chunk:
                return on_chunk(chunk, None, "Refine", None)

        effective_on_thinking = stream_chunk if stream else None
        content = await mock_chat_completion(
            mock["content"],
            mock["reasoning"],
            effective_on_thinking,
            stream=stream,
        )
        return _parse_keywords_response(content or "")

    cfg = merge_phase_config(api_config, "idea")
    ai_mode = api_config.get("aiMode", "llm")
    mode_cfg = api_config.get("modeConfig", {}).get(ai_mode, {})
    temperature = mode_cfg.get("ideaLlmTemperature")
    if temperature is not None:
        temperature = float(temperature)
    else:
        temperature = 0.3
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": idea},
    ]

    def _stream_cb(chunk: str):
        if on_chunk:
            return on_chunk(chunk, None, "Refine", None)

    try:
        full_content = await chat_completion(
            messages,
            cfg,
            on_chunk=_stream_cb,
            stream=True,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        text = full_content if isinstance(full_content, str) else str(full_content)
        return _parse_keywords_response(text)
    except Exception:
        return []
