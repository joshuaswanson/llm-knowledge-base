from __future__ import annotations

import re
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from kb.config import CONCEPTS_DIR, SOURCES_DIR, WIKI_DIR

app = FastAPI(title="KB Web UI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _strip_wikilinks(text: str) -> str:
    """Remove [[wikilinks]] so YAML parsing doesn't break."""
    return WIKILINK_RE.sub(r"\1", text)


def _parse_article(path: Path) -> dict:
    """Parse a markdown article, returning metadata + body."""
    text = path.read_text()
    meta: dict = {}
    body = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(_strip_wikilinks(parts[1])) or {}
            except yaml.YAMLError:
                meta = {}
            body = parts[2].strip()

    title = meta.get("title", path.stem.replace("-", " ").title())
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    related = meta.get("related", [])
    if isinstance(related, str):
        related = [r.strip() for r in related.split(",")]

    words = len(body.split())

    if path.is_relative_to(CONCEPTS_DIR):
        group = "concept"
        rel = path.relative_to(CONCEPTS_DIR)
        full_rel = f"concepts/{rel}"
    elif path.is_relative_to(SOURCES_DIR):
        group = "source"
        rel = path.relative_to(SOURCES_DIR)
        full_rel = f"sources/{rel}"
    else:
        group = "other"
        rel = path.relative_to(WIKI_DIR)
        full_rel = str(rel)

    return {
        "title": title,
        "tags": tags,
        "related": related,
        "path": full_rel,
        "group": group,
        "words": words,
        "markdown": body,
    }


def _all_articles() -> list[dict]:
    articles = []
    for d in [CONCEPTS_DIR, SOURCES_DIR]:
        if d.exists():
            for p in sorted(d.glob("*.md")):
                if p.name == ".gitkeep":
                    continue
                articles.append(_parse_article(p))
    return articles


# ---- Endpoints ----


@app.get("/api/status")
def status():
    articles = _all_articles()
    return {
        "concepts": sum(1 for a in articles if a["group"] == "concept"),
        "sources": sum(1 for a in articles if a["group"] == "source"),
        "total_words": sum(a["words"] for a in articles),
    }


@app.get("/api/articles")
def list_articles():
    return [
        {
            "title": a["title"],
            "tags": a["tags"],
            "path": a["path"],
            "group": a["group"],
            "words": a["words"],
        }
        for a in _all_articles()
    ]


@app.get("/api/article/{path:path}")
def get_article(path: str):
    full = WIKI_DIR / path
    if not full.exists() or not full.is_file():
        raise HTTPException(404, "Article not found")
    return _parse_article(full)


@app.get("/api/search")
def search_articles(q: str):
    from kb.search import search

    results = search(q)
    out = []
    for p, score, snippet in results:
        if p.is_relative_to(CONCEPTS_DIR):
            rel = f"concepts/{p.relative_to(CONCEPTS_DIR)}"
        elif p.is_relative_to(SOURCES_DIR):
            rel = f"sources/{p.relative_to(SOURCES_DIR)}"
        else:
            rel = str(p.relative_to(WIKI_DIR))
        title = p.stem.replace("-", " ").title()
        out.append({"title": title, "path": rel, "score": round(score, 4), "snippet": snippet})
    return out


class QueryRequest(BaseModel):
    question: str


@app.post("/api/query")
def query_endpoint(req: QueryRequest):
    from kb.query import query_kb

    answer = query_kb(req.question)
    return {"answer": answer}


class IngestRequest(BaseModel):
    url: str


@app.post("/api/ingest")
def ingest_endpoint(req: IngestRequest):
    from kb.ingest import ingest_url

    dest = ingest_url(req.url)
    if isinstance(dest, list):
        paths = [str(p.relative_to(p.parent.parent)) for p in dest]
        return {"status": "ok", "path": paths}
    return {"status": "ok", "path": str(dest.relative_to(dest.parent.parent))}


@app.post("/api/compile")
def compile_endpoint():
    from kb.compile import compile_kb

    result = compile_kb()
    return {"status": "ok", **result}


@app.get("/api/graph")
def graph_data():
    articles = _all_articles()
    nodes = []
    node_ids = set()

    for a in articles:
        node_id = a["title"]
        nodes.append({"id": node_id, "group": a["group"], "words": a["words"], "path": a["path"]})
        node_ids.add(node_id)

    edges = []
    for a in articles:
        # Find wikilinks in the markdown body
        links = WIKILINK_RE.findall(a["markdown"])
        for link in links:
            if link in node_ids:
                edges.append({"source": a["title"], "target": link})

    return {"nodes": nodes, "edges": edges}


# Mount static files last so API routes take priority
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
