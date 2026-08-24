from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_ENV_PATTERN = re.compile(r"^\$\{([A-Z0-9_]+)\}$")


def _expand_env(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, str):
        match = _ENV_PATTERN.match(value)
        if match:
            return os.getenv(match.group(1), "")
    return value


@dataclass(frozen=True)
class HarnessConfig:
    data: dict[str, Any]
    path: Path

    @property
    def runtime(self) -> dict[str, Any]:
        return self.data["runtime"]

    @property
    def profiles(self) -> dict[str, dict[str, Any]]:
        return self.data["profiles"]

    @property
    def routes(self) -> dict[str, list[str]]:
        return self.data["routes"]

    def resolve_path(self, key: str) -> Path:
        candidate = Path(self.runtime[key])
        if candidate.is_absolute():
            return candidate
        return (self.path.parent.parent / candidate).resolve()


def load_config(path: str | Path = "config/harness.json") -> HarnessConfig:
    config_path = Path(path)
    if not config_path.exists():
        example = config_path.with_name("harness.example.json")
        if example.exists():
            config_path = example
        else:
            raise FileNotFoundError(f"No harness config found at {path}")
    data = _expand_env(json.loads(config_path.read_text(encoding="utf-8")))
    for required in ("runtime", "orca", "profiles", "routes"):
        if required not in data:
            raise ValueError(f"Missing config section: {required}")
    return HarnessConfig(data=data, path=config_path.resolve())
