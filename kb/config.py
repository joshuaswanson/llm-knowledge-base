from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
WIKI_DIR = ROOT / "wiki"
CONCEPTS_DIR = WIKI_DIR / "concepts"
SOURCES_DIR = WIKI_DIR / "sources"
INDEX_PATH = WIKI_DIR / "INDEX.md"
STATE_PATH = ROOT / ".kb_state.json"

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096
