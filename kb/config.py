from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "kb.toml"

# Defaults
_DEFAULTS = {
    "provider": "ollama",
    "model": "",
    "ollama_base_url": "http://localhost:11434",
    "openai_base_url": "https://api.openai.com/v1",
    "max_concepts_per_compile": 20,
}

# Provider model defaults
_MODEL_DEFAULTS = {
    "ollama": "qwen3.5:27b",
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
}


def _load_config() -> dict:
    """Load config from kb.toml, falling back to defaults."""
    cfg = dict(_DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            # Use PyYAML for TOML-like parsing (simple key: value files)
            # For real TOML we'd need tomllib, but kb.toml is simple enough
            import tomllib  # noqa: F811
            with open(CONFIG_PATH, "rb") as f:
                file_cfg = tomllib.load(f)
            cfg.update(file_cfg)
        except Exception:
            pass
    # Env vars override config file
    if os.environ.get("KB_PROVIDER"):
        cfg["provider"] = os.environ["KB_PROVIDER"]
    if os.environ.get("KB_MODEL"):
        cfg["model"] = os.environ["KB_MODEL"]
    if os.environ.get("OLLAMA_BASE_URL"):
        cfg["ollama_base_url"] = os.environ["OLLAMA_BASE_URL"]
    if os.environ.get("OPENAI_BASE_URL"):
        cfg["openai_base_url"] = os.environ["OPENAI_BASE_URL"]
    return cfg


_cfg = _load_config()

# Paths
RAW_DIR = ROOT / "raw"
IMAGES_DIR = RAW_DIR / "images"
WIKI_DIR = ROOT / "wiki"
CONCEPTS_DIR = WIKI_DIR / "concepts"
SOURCES_DIR = WIKI_DIR / "sources"
INDEX_PATH = WIKI_DIR / "INDEX.md"
STATE_PATH = ROOT / ".kb_state.json"

# Provider settings
PROVIDER = _cfg["provider"]
OLLAMA_BASE_URL = _cfg["ollama_base_url"]
OPENAI_BASE_URL = _cfg["openai_base_url"]
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
MAX_TOKENS = 4096
MAX_CONCEPTS_PER_COMPILE = int(_cfg["max_concepts_per_compile"])


def get_model() -> str:
    return _cfg["model"] or _MODEL_DEFAULTS.get(PROVIDER, "gpt-4o")


def write_config(settings: dict) -> None:
    """Write settings to kb.toml."""
    lines = []
    for key, value in settings.items():
        if isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        elif isinstance(value, bool):
            lines.append(f"{key} = {'true' if value else 'false'}")
        else:
            lines.append(f"{key} = {value}")
    CONFIG_PATH.write_text("\n".join(lines) + "\n")
