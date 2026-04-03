# LLM Knowledge Base

An LLM-powered personal knowledge base. Ingest raw sources (articles, papers, files, URLs), compile them into an interlinked markdown wiki, and query the whole thing with natural language.

Inspired by [Andrej Karpathy's approach](https://x.com/karpathy/status/1908205689676280129) to using LLMs for building personal knowledge bases.

## How it works

1. **Ingest** raw sources into `raw/` (files or URLs, auto-extracted to markdown)
2. **Compile** sources into a structured wiki with cross-linked concept articles
3. **Query** the wiki with natural language questions
4. **Search** with full-text TF-IDF search
5. **Lint** for gaps, broken links, orphan articles, and improvement suggestions
6. View everything in **Obsidian** (or any markdown editor)

The LLM writes and maintains all wiki content. You rarely touch it directly.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/joshuaswanson/llm-knowledge-base.git
cd llm-knowledge-base
uv sync
```

### LLM provider

**Ollama (default, free):** Install [Ollama](https://ollama.com), then pull a model:

```bash
ollama pull qwen2.5:14b
```

**Anthropic (optional):** Set the provider and API key:

```bash
export KB_PROVIDER=anthropic
export ANTHROPIC_API_KEY="your-key-here"
```

**Configuration via environment variables:**

| Variable          | Default                                                         | Description             |
| ----------------- | --------------------------------------------------------------- | ----------------------- |
| `KB_PROVIDER`     | `ollama`                                                        | `ollama` or `anthropic` |
| `KB_MODEL`        | `qwen2.5:14b` (Ollama) / `claude-sonnet-4-20250514` (Anthropic) | Model name              |
| `OLLAMA_BASE_URL` | `http://localhost:11434`                                        | Ollama server URL       |

## Usage

```bash
# Ingest a URL
uv run kb ingest "https://example.com/interesting-article"

# Ingest a local file
uv run kb ingest path/to/paper.md

# Compile raw sources into wiki articles
uv run kb compile

# Recompile everything from scratch
uv run kb compile --force

# Ask a question
uv run kb query "What are the key themes across my sources?"

# Save answer to a file
uv run kb query "Summarize topic X" -o wiki/summaries/topic-x.md

# Search the wiki
uv run kb search "machine learning"

# Run health checks
uv run kb lint

# Quick structural check (no LLM calls)
uv run kb lint --no-llm

# Show stats
uv run kb status
```

## Viewing in Obsidian

Open the project root as an Obsidian vault. The `.obsidian/` config is included. The wiki uses `[[wikilinks]]` for cross-references, which Obsidian renders as clickable links with a graph view.

## Directory structure

```
raw/              Raw source documents (ingested markdown)
wiki/
  INDEX.md        Auto-maintained master index
  concepts/       Cross-linked concept articles
  sources/        Per-source summary articles
kb/               Python package (CLI + LLM logic)
```

## How compilation works

When you run `kb compile`:

1. New/changed raw sources are identified (tracked via `.kb_state.json`)
2. Each source is summarized into a wiki article in `wiki/sources/`
3. The LLM extracts key concepts and creates `[[wikilinks]]` between articles
4. New concept articles are generated in `wiki/concepts/` for linked concepts
5. `INDEX.md` is rebuilt with categorized links and word counts

Every compile run is incremental. Use `--force` to reprocess everything.

## Support

If you find this useful, [buy me a coffee](https://buymeacoffee.com/swanson).

<img src="assets/bmc_qr.png" alt="Buy Me a Coffee QR" width="200">
