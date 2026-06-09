"""Configuration API for reading and updating the local .env file."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.config import Settings

router = APIRouter(prefix="/api/config")

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = WORKSPACE_ROOT / ".env"
ENV_EXAMPLE_PATH = WORKSPACE_ROOT / ".env.example"
ENV_KEY_RE = re.compile(r"^(MAARS_[A-Z0-9_]+)=(.*)$")
SECTION_RE = re.compile(r"^#\s*---\s*(.*?)\s*---\s*$")

FIELD_META = {
    "MAARS_API_CONCURRENCY": {"type": "number"},
    "MAARS_API_REQUEST_INTERVAL": {"type": "number"},
    "MAARS_OUTPUT_LANGUAGE": {"type": "select", "options": ["Chinese", "English"]},
    "MAARS_RESEARCH_MAX_ITERATIONS": {"type": "number"},
    "MAARS_TEAM_MAX_DELEGATIONS": {"type": "number"},
    "MAARS_KAGGLE_API_TOKEN": {"type": "secret"},
    "MAARS_CODEX_REASONING_EFFORT": {"type": "select", "options": ["", "low", "medium", "high", "xhigh"]},
    "MAARS_CODEX_REFINE_REASONING_EFFORT": {"type": "select", "options": ["", "low", "medium", "high", "xhigh"]},
    "MAARS_CODEX_RESEARCH_REASONING_EFFORT": {"type": "select", "options": ["", "low", "medium", "high", "xhigh"]},
    "MAARS_CODEX_WRITE_REASONING_EFFORT": {"type": "select", "options": ["", "low", "medium", "high", "xhigh"]},
    "MAARS_CODEX_POLISH_REASONING_EFFORT": {"type": "select", "options": ["", "low", "medium", "high", "xhigh"]},
    "MAARS_CODEX_VERBOSITY": {"type": "select", "options": ["", "low", "medium", "high"]},
    "MAARS_CODEX_TIMEOUT": {"type": "number"},
    "MAARS_CODEX_INHERIT_PROXY": {"type": "boolean"},
    "MAARS_CODEX_SANDBOX_PROVIDER": {"type": "select", "options": ["local", "docker"]},
}


class EnvUpdateRequest(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


@dataclass
class EnvLine:
    raw: str
    key: str | None = None
    value: str = ""
    comment: str = ""
    section: str = ""
    notes: list[str] = field(default_factory=list)


def _split_value_comment(raw_value: str) -> tuple[str, str]:
    if "#" not in raw_value:
        return raw_value.strip(), ""
    value, comment = raw_value.split("#", 1)
    return value.rstrip(), comment.strip()


def _parse_env_file(path: Path) -> tuple[list[EnvLine], dict[str, str]]:
    lines: list[EnvLine] = []
    values: dict[str, str] = {}
    current_section = ""
    pending_notes: list[str] = []
    if not path.exists():
        return lines, values
    for raw in path.read_text(encoding="utf-8").splitlines():
        section_match = SECTION_RE.match(raw.strip())
        if section_match:
            current_section = section_match.group(1).strip()
            pending_notes = []
            lines.append(EnvLine(raw=raw, section=current_section))
            continue
        key_match = ENV_KEY_RE.match(raw)
        if key_match:
            key = key_match.group(1)
            value, comment = _split_value_comment(key_match.group(2))
            values[key] = value
            lines.append(EnvLine(
                raw=raw,
                key=key,
                value=value,
                comment=comment,
                section=current_section,
                notes=pending_notes,
            ))
            pending_notes = []
            continue
        stripped = raw.strip()
        if stripped.startswith("#") and not stripped.startswith("# ---"):
            pending_notes.append(stripped.lstrip("#").strip())
        elif stripped:
            pending_notes = []
        lines.append(EnvLine(raw=raw, section=current_section))
    return lines, values


def _ensure_env_exists() -> None:
    if ENV_PATH.exists():
        return
    if not ENV_EXAMPLE_PATH.exists():
        raise HTTPException(status_code=500, detail=".env.example not found")
    ENV_PATH.write_text(ENV_EXAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8")


def _settings_kwargs(values: dict[str, str]) -> dict[str, str]:
    return {
        key.removeprefix("MAARS_").lower(): value
        for key, value in values.items()
        if key.startswith("MAARS_")
    }


def _validate_env_shape(values: dict[str, str]) -> None:
    for key, value in values.items():
        if not ENV_KEY_RE.match(f"{key}="):
            raise HTTPException(status_code=400, detail=f"Invalid env key: {key}")
        if "\n" in value or "\r" in value:
            raise HTTPException(status_code=400, detail=f"Invalid multiline value for {key}")


def _validate_values(values: dict[str, str]) -> None:
    _validate_env_shape(values)
    try:
        Settings(_env_file=None, **_settings_kwargs(values))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _entry(line: EnvLine, current_values: dict[str, str]) -> dict:
    meta = FIELD_META.get(line.key or "", {"type": "text"})
    return {
        "key": line.key,
        "value": current_values.get(line.key or "", line.value),
        "default": line.value,
        "comment": line.comment,
        "notes": line.notes,
        "section": line.section,
        "type": meta.get("type", "text"),
        "options": meta.get("options", []),
    }


def _sections(example_lines: list[EnvLine], current_values: dict[str, str]) -> list[dict]:
    sections: list[dict] = []
    by_title: dict[str, dict] = {}
    seen: set[str] = set()
    for line in example_lines:
        if not line.key:
            continue
        title = line.section or "General"
        section = by_title.get(title)
        if section is None:
            section = {"title": title, "entries": []}
            by_title[title] = section
            sections.append(section)
        section["entries"].append(_entry(line, current_values))
        seen.add(line.key)
    custom = [
        {"key": key, "value": value, "default": "", "comment": "", "notes": [], "section": "Custom", "type": "text", "options": []}
        for key, value in sorted(current_values.items())
        if key not in seen
    ]
    if custom:
        sections.append({"title": "Custom", "entries": custom})
    return sections


def _render_env(example_lines: list[EnvLine], values: dict[str, str], existing_values: dict[str, str]) -> str:
    rendered: list[str] = []
    seen: set[str] = set()
    for line in example_lines:
        if not line.key:
            rendered.append(line.raw)
            continue
        value = values.get(line.key, existing_values.get(line.key, line.value))
        suffix = f"  # {line.comment}" if line.comment else ""
        rendered.append(f"{line.key}={value}{suffix}")
        seen.add(line.key)
    extras = [(key, value) for key, value in sorted(values.items()) if key not in seen]
    if extras:
        rendered.extend(["", "# --- Custom ---"])
        rendered.extend(f"{key}={value}" for key, value in extras)
    return "\n".join(rendered).rstrip() + "\n"


@router.get("/env")
async def get_env_config():
    _ensure_env_exists()
    example_lines, example_values = _parse_env_file(ENV_EXAMPLE_PATH)
    _, current_values = _parse_env_file(ENV_PATH)
    merged_values = {**example_values, **current_values}
    return {
        "path": str(ENV_PATH),
        "restart_required": True,
        "sections": _sections(example_lines, merged_values),
        "raw": ENV_PATH.read_text(encoding="utf-8"),
    }


@router.put("/env")
async def update_env_config(req: EnvUpdateRequest):
    _ensure_env_exists()
    example_lines, example_values = _parse_env_file(ENV_EXAMPLE_PATH)
    _, existing_values = _parse_env_file(ENV_PATH)
    merged_values = {**example_values, **existing_values, **req.values}
    _validate_values(merged_values)
    ENV_PATH.write_text(_render_env(example_lines, merged_values, existing_values), encoding="utf-8")
    return {"saved": True, "restart_required": True, "path": str(ENV_PATH)}
