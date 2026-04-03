import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
WIKI_DIR = ROOT / "wiki"
CONCEPTS_DIR = WIKI_DIR / "concepts"
SOURCES_DIR = WIKI_DIR / "sources"
INDEX_PATH = WIKI_DIR / "INDEX.md"
STATE_PATH = ROOT / ".kb_state.json"

# Provider: "ollama" (default, free) or "anthropic"
PROVIDER = os.environ.get("KB_PROVIDER", "ollama")

# Ollama settings
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("KB_MODEL", "qwen3:8b")

# Anthropic settings
ANTHROPIC_MODEL = os.environ.get("KB_MODEL", "claude-sonnet-4-20250514")
MAX_TOKENS = 4096
