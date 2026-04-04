# LLM Knowledge Base

An LLM-powered personal knowledge base. Ingest raw sources (articles, papers, YouTube videos, files), compile them into an interlinked markdown wiki, and query the whole thing with natural language. Comes with a web UI, interactive graph visualization, and Obsidian compatibility.

Inspired by [Andrej Karpathy's approach](https://x.com/karpathy/status/2039805659525644595) to using LLMs for building personal knowledge bases.

## How it works

1. **Ingest** raw sources into `raw/` (URLs, YouTube videos, files, auto-extracted to markdown)
2. **Compile** sources into a structured wiki with cross-linked concept articles
3. **Query** the wiki with natural language questions (CLI or web chat)
4. **Search** with full-text TF-IDF search
5. **Lint** for gaps, broken links, orphan articles, and improvement suggestions
6. **Browse** everything in the web UI or Obsidian
7. **Graph** view shows how all your concepts connect

The LLM writes and maintains all wiki content. You rarely touch it directly. Every query can be filed back into the wiki, so the system gets smarter the more you use it.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/joshuaswanson/llm-knowledge-base.git
cd llm-knowledge-base
uv sync
```

### LLM provider

Supports three provider types: **Ollama** (local, free), **Anthropic**, or any **OpenAI-compatible API** (OpenAI, OpenRouter, Together, Groq, vLLM, LM Studio, etc.).

**Ollama (default):**

```bash
ollama pull qwen3.5:27b
```

**OpenAI-compatible API** (works with OpenRouter, Together, Groq, etc.):

```bash
export KB_PROVIDER=openai
export OPENAI_BASE_URL=https://openrouter.ai/api/v1  # or any compatible endpoint
export OPENAI_API_KEY=your-key
export KB_MODEL=anthropic/claude-sonnet-4             # model name for that provider
```

**Anthropic:**

```bash
export KB_PROVIDER=anthropic
export ANTHROPIC_API_KEY=your-key
```

**Environment variables:**

| Variable            | Default                     | Description                                                           |
| ------------------- | --------------------------- | --------------------------------------------------------------------- |
| `KB_PROVIDER`       | `ollama`                    | `ollama`, `anthropic`, or `openai`                                    |
| `KB_MODEL`          | auto per provider           | Model name (e.g. `qwen3.5:27b`, `gpt-4o`, `claude-sonnet-4-20250514`) |
| `OLLAMA_BASE_URL`   | `http://localhost:11434`    | Ollama server URL                                                     |
| `OPENAI_BASE_URL`   | `https://api.openai.com/v1` | OpenAI-compatible API base URL                                        |
| `OPENAI_API_KEY`    |                             | API key for OpenAI-compatible providers                               |
| `ANTHROPIC_API_KEY` |                             | Anthropic API key                                                     |

## Quick start

```bash
uv run kb init              # interactive setup (pick provider, model)
uv run kb ingest <url>      # add a source
uv run kb compile           # compile into wiki
uv run kb serve             # open web UI
```

## Usage

### CLI

```bash
# Ingest sources (URLs, YouTube, papers, files, images, datasets)
uv run kb ingest "https://arxiv.org/abs/2510.21842"
uv run kb ingest "https://youtube.com/watch?v=..."
uv run kb ingest paper.pdf notes.md photo.png data.csv

# Batch ingest with auto-compile
uv run kb ingest url1 url2 file1.md --compile

# Ingest a GitHub/GitLab repo (clones, reads README + structure)
uv run kb ingest-repo "https://github.com/user/repo"

# Ingest a podcast RSS feed (grabs transcripts when available)
uv run kb ingest-podcast "https://feeds.example.com/podcast.xml"
uv run kb ingest-podcast "https://feeds.example.com/podcast.xml" --max-episodes 10

# Import browser bookmarks (Chrome/Firefox/Safari HTML export)
uv run kb import-bookmarks ~/Downloads/bookmarks.html

# Import Twitter/X bookmarks (JSON data export)
uv run kb import-bookmarks ~/Downloads/twitter-bookmarks.json

# Compile raw sources into wiki articles
uv run kb compile
uv run kb compile --force    # recompile everything

# Ask a question (answer saved back to wiki with --save)
uv run kb query "What are the key themes across my sources?"
uv run kb query "Summarize topic X" --save
uv run kb query "Compare A and B" -o wiki/comparisons/a-vs-b.md

# Search the wiki
uv run kb search "machine learning"

# Generate Marp slide deck from wiki content
uv run kb slides "topic name"
uv run kb slides "RAG techniques" -o slides/rag.md

# Run health checks
uv run kb lint
uv run kb lint --no-llm    # structural checks only, no API calls

# Show stats
uv run kb status

# Generate a matplotlib chart from wiki data
uv run kb chart "tag distribution"
uv run kb chart "word counts by source" -o wiki/charts/words.png

# Watch a directory for new files and auto-ingest
uv run kb watch ~/Downloads/research --compile-after

# Get a browser bookmarklet for one-click saving
uv run kb bookmarklet
# Or visit http://localhost:3000/api/bookmarklet to drag it to your bookmarks bar
```

### Web UI

```bash
uv run kb serve
```

Opens a web dashboard at `http://localhost:3000` with:

- **Dashboard**: Stats, quick ingest, compile button
- **Browse**: Read articles with rendered markdown and clickable wikilinks
- **Search**: Full-text search with relevance scores
- **Chat**: Conversational Q&A against your knowledge base
- **Graph**: Interactive D3 force-directed graph of concept connections

Light/dark mode toggle in the sidebar. Keyboard shortcuts: press 1-5 to switch between views.

### Obsidian

Open the project root as an Obsidian vault. The `.obsidian/` config is included. The wiki uses `[[wikilinks]]` for cross-references, which Obsidian renders as clickable links with a graph view.

## Directory structure

```
raw/              Raw source documents (ingested markdown)
wiki/
  INDEX.md        Auto-maintained master index
  concepts/       Cross-linked concept articles
  sources/        Per-source summary articles
  queries/        Saved Q&A results
  slides/         Generated slide decks
kb/               Python package
  cli.py          CLI commands
  web.py          FastAPI web UI
  compile.py      Wiki compilation
  query.py        Q&A engine
  search.py       TF-IDF search
  ingest.py       Source ingestion (URLs, YouTube, repos, podcasts, images, datasets)
  slides.py       Marp slide generation
  lint.py         Health checks
  llm.py          LLM provider abstraction
  static/         Web UI frontend
```

## How compilation works

When you run `kb compile`:

1. New/changed raw sources are identified (tracked via `.kb_state.json`)
2. Each source is summarized into a wiki article in `wiki/sources/`
3. The LLM extracts key concepts and creates `[[wikilinks]]` between articles
4. New concept articles are generated in `wiki/concepts/` for linked concepts
5. Backlinks are generated (each article lists what links to it)
6. `INDEX.md` is rebuilt with brief summaries and word counts
7. Images referenced in sources are downloaded locally to `raw/images/`

Every compile run is incremental. Use `--force` to reprocess everything. Progress bars show status, and compilation survives errors (skips failed items and continues).

## Configuration

Settings are stored in `kb.toml` (created by `kb init`). Environment variables override the config file.

```toml
provider = "ollama"
model = "qwen3.5:27b"
max_concepts_per_compile = 20
```

## Support

If you find this useful, [buy me a coffee](https://buymeacoffee.com/swanson).

<img src="assets/bmc_qr.png" alt="Buy Me a Coffee QR" width="200">
