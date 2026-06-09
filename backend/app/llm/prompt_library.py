"""Versioned prompt loader. Prompts live as YAML and carry id + version + schema."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined

from app.core.errors import AppError

_PROMPTS_ROOT = Path(__file__).parent / "prompts"


@dataclass(slots=True)
class PromptTemplate:
    id: str
    version: str
    system: str
    user_template: str
    description: str = ""


class PromptLibrary:
    def __init__(self, root: Path = _PROMPTS_ROOT) -> None:
        self._root = root
        self._cache: dict[tuple[str, str], PromptTemplate] = {}
        self._jinja = Environment(undefined=StrictUndefined, autoescape=False)

    def load(self, prompt_id: str, version: str = "v1") -> PromptTemplate:
        key = (prompt_id, version)
        if key in self._cache:
            return self._cache[key]
        path = self._root / f"{prompt_id.replace('.', '/')}.{version}.yaml"
        if not path.exists():
            raise AppError(
                f"Prompt template not found: {prompt_id} {version}",
                status_code=500,
                code="prompt.not_found",
            )
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        tmpl = PromptTemplate(
            id=data["id"],
            version=str(data.get("version", version)),
            system=data["system"],
            user_template=data["user"],
            description=data.get("description", ""),
        )
        self._cache[key] = tmpl
        return tmpl

    def render(self, prompt_id: str, version: str, **vars) -> tuple[str, str, PromptTemplate]:
        tmpl = self.load(prompt_id, version)
        user = self._jinja.from_string(tmpl.user_template).render(**vars)
        return tmpl.system, user, tmpl


@lru_cache
def get_prompt_library() -> PromptLibrary:
    return PromptLibrary()
