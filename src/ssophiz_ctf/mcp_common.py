from __future__ import annotations

import os

from .config import HarnessConfig, load_config
from .state import StateStore


def current_config() -> HarnessConfig:
    return load_config(os.getenv("SSOPHIZ_CONFIG", "config/harness.json"))


def current_store() -> StateStore:
    config = current_config()
    return StateStore(config.resolve_path("state_db"))
