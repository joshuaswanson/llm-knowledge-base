from __future__ import annotations

import re
import tempfile
from pathlib import Path

import yaml
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="LLM Knowledge Base", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str


class IngestRequest(BaseModel):
    url: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_frontmatter(path: Path) -> dict:
    text = path.read_text()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            # Strip [[wikilinks]] from frontmatter before parsing
            fm = re.sub(r"\[\[([^\]]+)\]\]", r"\1", parts[1])
            try:
                return yaml.safe_load(fm) or {}
            except yaml.YAMLError:
                return {}
    return {}


def _read_body(path: Path) -> str:
    text = path.read_text()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text


def _word_count(path: Path) -> int:
    return len(_read_body(path).split())


def _all_articles() -> list[dict]:
    from kb.config import CONCEPTS_DIR, SOURCES_DIR, WIKI_DIR

    articles = []
    for directory, group in [(CONCEPTS_DIR, "concept"), (SOURCES_DIR, "source")]:
        if not directory.exists():
            continue
        for p in sorted(directory.glob("*.md")):
            meta = _read_frontmatter(p)
            rel_path = p.relative_to(WIKI_DIR)
            articles.append({
                "title": meta.get("title", p.stem.replace("-", " ").title()),
                "tags": meta.get("tags", []),
                "related": meta.get("related", []),
                "path": str(rel_path),
                "group": group,
                "words": _word_count(p),
            })
    return articles


def _resolve_article_path(rel_path: str) -> Path:
    from kb.config import WIKI_DIR

    full = (WIKI_DIR / rel_path).resolve()
    # Prevent path traversal outside WIKI_DIR
    if not str(full).startswith(str(WIKI_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Path traversal not allowed")
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail="Article not found")
    return full


def _wikilink_to_html(body: str) -> str:
    """Convert [[Wikilink]] and [[path|Display]] to clickable HTML links."""
    def _replace(m: re.Match) -> str:
        inner = m.group(1)
        if "|" in inner:
            target, display = inner.split("|", 1)
        else:
            target, display = inner, inner
        # Build a URL-safe path fragment
        slug = target.strip().lower()
        slug = re.sub(r"[^\w\s/-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug).strip("-")
        return f'<a class="wikilink" href="/article/{slug}">{display.strip()}</a>'

    return re.sub(r"\[\[([^\]]+)\]\]", _replace, body)


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@app.get("/api/articles")
async def list_articles():
    return _all_articles()


@app.get("/api/article/{path:path}")
async def get_article(path: str):
    full = _resolve_article_path(path)
    meta = _read_frontmatter(full)
    body = _read_body(full)
    html = _wikilink_to_html(body)
    return {
        "title": meta.get("title", full.stem.replace("-", " ").title()),
        "tags": meta.get("tags", []),
        "related": meta.get("related", []),
        "path": path,
        "words": len(body.split()),
        "markdown": body,
        "html": html,
    }


@app.get("/api/search")
async def search_articles(q: str = Query(..., min_length=1)):
    from kb.search import search

    results = search(q, top_k=20)
    from kb.config import WIKI_DIR

    items = []
    for path, score, snippet in results:
        meta = _read_frontmatter(path)
        try:
            rel = str(path.relative_to(WIKI_DIR))
        except ValueError:
            rel = path.name
        items.append({
            "title": meta.get("title", path.stem.replace("-", " ").title()),
            "path": rel,
            "score": round(score, 4),
            "snippet": snippet,
        })
    return items


@app.post("/api/query")
async def query_endpoint(req: QueryRequest):
    from kb.query import query_kb

    answer = query_kb(req.question)
    return {"question": req.question, "answer": answer}


@app.post("/api/ingest")
async def ingest_endpoint(
    req: IngestRequest | None = None,
    file: UploadFile | None = File(None),
):
    from kb.ingest import ingest_file, ingest_url

    if req and req.url:
        dest = ingest_url(req.url)
        return {"status": "ok", "path": str(dest), "source": req.url}

    if file and file.filename:
        suffix = Path(file.filename).suffix or ".txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)
        try:
            dest = ingest_file(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
        return {"status": "ok", "path": str(dest), "filename": file.filename}

    raise HTTPException(status_code=400, detail="Provide a URL or upload a file")


@app.get("/api/bookmarklet", response_class=HTMLResponse)
async def bookmarklet_endpoint(server: str = "http://localhost:3000"):
    bookmarklet_js = _bookmarklet_js(server)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Knowledge Base Bookmarklet</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 Helvetica, Arial, sans-serif;
    max-width: 640px;
    margin: 3rem auto;
    padding: 0 1rem;
    line-height: 1.6;
    color: #1a1a1a;
    background: #fafafa;
  }}
  h1 {{ font-size: 1.4rem; }}
  .bookmarklet-link {{
    display: inline-block;
    padding: 0.5rem 1.2rem;
    background: #2563eb;
    color: #fff;
    border-radius: 6px;
    text-decoration: none;
    font-weight: 600;
    font-size: 0.95rem;
    cursor: grab;
    user-select: none;
  }}
  .bookmarklet-link:hover {{ background: #1d4ed8; }}
  code {{
    background: #e5e7eb;
    padding: 0.15rem 0.35rem;
    border-radius: 3px;
    font-size: 0.85rem;
  }}
  pre {{
    background: #1e293b;
    color: #e2e8f0;
    padding: 1rem;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 0.82rem;
    line-height: 1.5;
  }}
  ol li {{ margin-bottom: 0.5rem; }}
  .config-note {{
    margin-top: 2rem;
    padding: 0.75rem 1rem;
    background: #fef3c7;
    border-left: 3px solid #f59e0b;
    border-radius: 4px;
    font-size: 0.9rem;
  }}
</style>
</head>
<body>
<h1>Ingest to Knowledge Base</h1>

<p>Drag this button to your bookmarks bar:</p>

<p><a class="bookmarklet-link" href="{bookmarklet_js}">Save to KB</a></p>

<h2>How to use</h2>
<ol>
  <li>Drag the <strong>Save to KB</strong> button above into your browser's bookmarks bar.</li>
  <li>Navigate to any page you want to save.</li>
  <li>Click the bookmarklet. A small notification will confirm success or failure.</li>
</ol>

<h2>Raw JavaScript</h2>
<pre>{bookmarklet_js}</pre>

<div class="config-note">
  <strong>Server URL:</strong> Currently configured for <code>{server}</code>.<br>
  To change it, visit <code>/api/bookmarklet?server=http://your-host:port</code>.
</div>
</body>
</html>"""


def _bookmarklet_js(server: str = "http://localhost:3000") -> str:
    """Return the bookmarklet JavaScript as a javascript: URL."""
    server = server.rstrip("/")
    return (
        "javascript:void((function(){"
        "var s='" + server + "';"
        "var u=location.href;"
        "var n=document.createElement('div');"
        "n.style.cssText='position:fixed;top:16px;right:16px;z-index:2147483647;"
        "padding:12px 20px;border-radius:8px;font:14px/1.4 -apple-system,sans-serif;"
        "color:#fff;background:#2563eb;box-shadow:0 4px 12px rgba(0,0,0,.15);"
        "transition:opacity .3s';"
        "n.textContent='Saving to KB...';"
        "document.body.appendChild(n);"
        "fetch(s+'/api/ingest',{method:'POST',"
        "headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({url:u})})"
        ".then(function(r){if(!r.ok)throw new Error(r.status);return r.json()})"
        ".then(function(d){"
        "n.style.background='#16a34a';"
        "n.textContent='Saved to KB';"
        "setTimeout(function(){n.style.opacity='0';"
        "setTimeout(function(){n.remove()},400)},2000)})"
        ".catch(function(e){"
        "n.style.background='#dc2626';"
        "n.textContent='Failed: '+e.message;"
        "setTimeout(function(){n.style.opacity='0';"
        "setTimeout(function(){n.remove()},400)},3000)})"
        "})())"
    )


@app.post("/api/compile")
async def compile_endpoint():
    from kb.compile import compile_kb

    result = compile_kb(force=False)
    return {"status": "ok", **result}


@app.get("/api/graph")
async def graph_endpoint():
    from kb.config import CONCEPTS_DIR, SOURCES_DIR, WIKI_DIR

    nodes = []
    edges = []
    seen_edges: set[tuple[str, str]] = set()

    for directory, group in [(CONCEPTS_DIR, "concept"), (SOURCES_DIR, "source")]:
        if not directory.exists():
            continue
        for p in sorted(directory.glob("*.md")):
            meta = _read_frontmatter(p)
            title = meta.get("title", p.stem.replace("-", " ").title())
            body = _read_body(p)
            words = len(body.split())
            nodes.append({"id": title, "group": group, "words": words})

            # Extract wikilinks
            links = re.findall(r"\[\[([^\]|]+)", p.read_text())
            for link in links:
                target = link.split("/")[-1].strip()
                edge = (title, target)
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    edges.append({"source": title, "target": target})

    return {"nodes": nodes, "edges": edges}


@app.get("/api/status")
async def status_endpoint():
    from kb.config import CONCEPTS_DIR, SOURCES_DIR

    concept_count = 0
    source_count = 0
    total_words = 0

    if CONCEPTS_DIR.exists():
        for p in CONCEPTS_DIR.glob("*.md"):
            concept_count += 1
            total_words += _word_count(p)

    if SOURCES_DIR.exists():
        for p in SOURCES_DIR.glob("*.md"):
            source_count += 1
            total_words += _word_count(p)

    return {
        "concepts": concept_count,
        "sources": source_count,
        "total_words": total_words,
    }


# ---------------------------------------------------------------------------
# Static file serving (must be last so /api/ routes take priority)
# ---------------------------------------------------------------------------

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
