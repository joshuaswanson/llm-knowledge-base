from __future__ import annotations

import json
import re
from pathlib import Path

import click
import yaml

from kb.config import CONCEPTS_DIR, IMAGES_DIR, RAW_DIR, SOURCES_DIR, STATE_PATH
from kb.index import rebuild_index
from kb.llm import ask

SYSTEM_PROMPT = """\
You are a knowledge base compiler. Your job is to process raw source documents \
and produce well-structured wiki articles in markdown format.

Rules:
- Use Obsidian-compatible wiki links: [[Concept Name]] to link between concepts IN THE BODY TEXT ONLY
- Include YAML frontmatter with: title, tags (list of plain strings), related (list of plain strings, NO [[ ]] brackets)
- IMPORTANT: In YAML frontmatter, use plain strings only. NO wiki link syntax. Write related as:
  related:
    - Large Language Model
    - Vector Database
  NOT: related: [[Large Language Model]], [[Vector Database]]
- Write clear, information-dense prose. No filler.
- Organize with headings (##, ###). Use bullet lists for key points.
- Preserve specific facts, numbers, quotes, and citations from the source
- When you identify distinct concepts, create [[links]] to them in the body text even if articles \
don't exist yet. These become candidates for future articles.
"""


def _load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"sources": {}}


def _save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2))


def _read_raw_source(path: Path) -> tuple[dict, str]:
    text = path.read_text()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()
            return frontmatter, body
    return {}, text


def _get_existing_concepts() -> list[str]:
    CONCEPTS_DIR.mkdir(parents=True, exist_ok=True)
    return [p.stem for p in CONCEPTS_DIR.glob("*.md")]


def _collect_image_refs(body: str) -> list[str]:
    """Extract local image paths referenced in the body text."""
    refs = re.findall(r"!\[[^\]]*\]\((images/[^)]+)\)", body)
    # Only keep paths that actually exist on disk
    return [r for r in refs if (RAW_DIR / r).exists()]


def _compile_source_summary(meta: dict, body: str) -> str:
    title = meta.get("title", "Untitled")
    existing = _get_existing_concepts()
    existing_str = ", ".join(existing[:100]) if existing else "(none yet)"

    image_refs = _collect_image_refs(body)
    image_note = ""
    if image_refs:
        paths_str = "\n".join(f"  - {ref}" for ref in image_refs)
        image_note = (
            f"\nThis source references the following images (you cannot see them, "
            f"but note their presence and preserve the references):\n{paths_str}\n"
        )

    prompt = f"""\
Summarize the following source document into a wiki article.

Source title: {title}
Source type: {meta.get('source_type', 'unknown')}
Source URL: {meta.get('source_url', 'N/A')}
{image_note}
Existing concepts in the wiki (link to these with [[Name]] where relevant):
{existing_str}

---
SOURCE CONTENT:
{body[:20000]}
---

Write a comprehensive summary article for this source. Include:
1. YAML frontmatter with title, tags, and related concepts
2. A brief overview paragraph
3. Key points and takeaways organized by topic
4. Any specific data, quotes, or findings worth preserving
5. Links to existing and new concepts using [[Concept Name]] syntax
6. Preserve any image references from the source (![alt](images/...)) in relevant sections

Output ONLY the markdown article content (starting with ---frontmatter---)."""

    return ask(prompt, system=SYSTEM_PROMPT)


def _extract_concepts(source_articles: list[str]) -> list[str]:
    all_links = set()
    for article in source_articles:
        links = re.findall(r"\[\[([^\]]+)\]\]", article)
        all_links.update(links)

    existing = set(_get_existing_concepts())
    return sorted(all_links - existing)


def _compile_concept_article(concept: str, source_articles: list[str]) -> str:
    existing = _get_existing_concepts()
    existing_str = ", ".join(existing[:100]) if existing else "(none yet)"

    context = "\n\n---\n\n".join(source_articles[:10])

    prompt = f"""\
Write a wiki article about the concept: "{concept}"

Use the following source articles as context (these are summaries from the knowledge base):

{context[:15000]}

Existing concepts in the wiki (link to these with [[Name]] where relevant):
{existing_str}

Write a comprehensive article about "{concept}". Include:
1. YAML frontmatter with title, tags, and related concepts
2. A clear definition/overview
3. Key details from the source material
4. Connections to other concepts using [[Concept Name]] links
5. Organized with clear headings

Output ONLY the markdown article content (starting with ---frontmatter---)."""

    return ask(prompt, system=SYSTEM_PROMPT)


def compile_kb(force: bool = False) -> dict:
    state = _load_state()
    sources = state.get("sources", {})

    uncompiled = []
    for filename, info in sources.items():
        if force or not info.get("compiled", False):
            raw_path = RAW_DIR / filename
            if raw_path.exists():
                uncompiled.append((filename, raw_path, info))

    if not uncompiled:
        click.echo("All sources are already compiled. Use --force to recompile.")
        return {"sources_compiled": 0, "concepts_created": 0}

    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    CONCEPTS_DIR.mkdir(parents=True, exist_ok=True)

    source_articles = []
    for filename, raw_path, info in uncompiled:
        meta, body = _read_raw_source(raw_path)
        title = meta.get("title", info.get("title", "Untitled"))

        click.echo(f"  Compiling source: {title}")
        article = _compile_source_summary(meta, body)
        source_articles.append(article)

        slug = re.sub(r"[^\w\s-]", "", title.lower().strip())
        slug = re.sub(r"[\s_]+", "-", slug)[:80].strip("-")
        dest = SOURCES_DIR / f"{slug}.md"
        dest.write_text(article)

        state["sources"][filename]["compiled"] = True

    # Extract new concepts from all source articles
    new_concepts = _extract_concepts(source_articles)

    # Also gather existing source articles for context
    all_source_texts = []
    for p in SOURCES_DIR.glob("*.md"):
        all_source_texts.append(p.read_text())

    concepts_created = 0
    if new_concepts:
        click.echo(f"  Found {len(new_concepts)} new concepts to create")
        for concept in new_concepts[:20]:  # Cap at 20 per compile run
            click.echo(f"  Creating concept: {concept}")
            article = _compile_concept_article(concept, all_source_texts)
            slug = re.sub(r"[^\w\s-]", "", concept.lower().strip())
            slug = re.sub(r"[\s_]+", "-", slug)[:80].strip("-")
            dest = CONCEPTS_DIR / f"{slug}.md"
            dest.write_text(article)
            concepts_created += 1

    _save_state(state)
    rebuild_index()

    return {
        "sources_compiled": len(uncompiled),
        "concepts_created": concepts_created,
    }
