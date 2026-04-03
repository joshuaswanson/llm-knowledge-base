import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
IMAGES_DIR = RAW_DIR / "images"
WIKI_DIR = ROOT / "wiki"
CONCEPTS_DIR = WIKI_DIR / "concepts"
SOURCES_DIR = WIKI_DIR / "sources"
INDEX_PATH = WIKI_DIR / "INDEX.md"
STATE_PATH = ROOT / ".kb_state.json"

# Provider: "ollama" (default, free), "anthropic", or "openai" (any OpenAI-compatible API)
PROVIDER = os.environ.get("KB_PROVIDER", "ollama")

# Model name (used by all providers)
MODEL = os.environ.get("KB_MODEL", "")

# Ollama
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# OpenAI-compatible API (works with OpenAI, OpenRouter, Together, Groq, vLLM, LM Studio, etc.)
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Anthropic
MAX_TOKENS = 4096

# Defaults per provider
_DEFAULTS = {
    "ollama": "qwen3.5:27b",
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
}


def get_model() -> str:
    return MODEL or _DEFAULTS.get(PROVIDER, "gpt-4o")
