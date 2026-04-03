from __future__ import annotations

import re

import yaml

from kb.config import CONCEPTS_DIR, SOURCES_DIR
from kb.llm import ask

SYSTEM_PROMPT = """\
You are a knowledge base quality auditor. Analyze the wiki content and provide \
actionable feedback to improve its quality, completeness, and consistency."""


def _gather_all_articles() -> list[tuple[str, str, dict]]:
    articles = []
    for d in [CONCEPTS_DIR, SOURCES_DIR]:
        if d.exists():
            for p in d.glob("*.md"):
                text = p.read_text()
                meta = {}
                if text.startswith("---"):
                    parts = text.split("---", 2)
                    if len(parts) >= 3:
                        meta = yaml.safe_load(parts[1]) or {}
                articles.append((p.name, text, meta))
    return articles


def _find_broken_links(articles: list[tuple[str, str, dict]]) -> list[str]:
    existing = set()
    for d in [CONCEPTS_DIR, SOURCES_DIR]:
        if d.exists():
            for p in d.glob("*.md"):
                existing.add(p.stem.lower())

    issues = []
    for name, text, _ in articles:
        links = re.findall(r"\[\[([^\]|]+)", text)
        for link in links:
            # Strip path prefixes for matching
            link_stem = link.split("/")[-1].lower().strip()
            slug = re.sub(r"[^\w\s-]", "", link_stem)
            slug = re.sub(r"[\s_]+", "-", slug).strip("-")
            if slug not in existing and link_stem not in existing:
                issues.append(f"Broken link [[{link}]] in {name}")
    return issues


def _find_orphans(articles: list[tuple[str, str, dict]]) -> list[str]:
    all_links = set()
    for _, text, _ in articles:
        links = re.findall(r"\[\[([^\]|]+)", text)
        for link in links:
            all_links.add(link.split("/")[-1].lower().strip())

    orphans = []
    for d in [CONCEPTS_DIR, SOURCES_DIR]:
        if d.exists():
            for p in d.glob("*.md"):
                if p.stem.lower() not in all_links and p.name != "INDEX.md":
                    orphans.append(f"Orphan article (no incoming links): {p.name}")
    return orphans


def lint_kb(use_llm: bool = True) -> dict:
    articles = _gather_all_articles()

    if not articles:
        return {"issues": ["Knowledge base is empty. Ingest and compile some sources first."], "suggestions": []}

    issues = []
    suggestions = []

    # Structural checks
    issues.extend(_find_broken_links(articles))
    issues.extend(_find_orphans(articles))

    # Check for missing frontmatter
    for name, text, meta in articles:
        if not meta:
            issues.append(f"Missing frontmatter: {name}")
        elif not meta.get("tags"):
            issues.append(f"Missing tags in frontmatter: {name}")

    # LLM-powered analysis
    if use_llm and articles:
        summaries = []
        for name, _, meta in articles[:50]:
            title = meta.get("title", name)
            tags = meta.get("tags", [])
            summaries.append(f"- {title} (tags: {', '.join(tags) if tags else 'none'})")

        article_list = "\n".join(summaries)
        prompt = f"""\
Analyze this knowledge base and suggest improvements. Here are all articles:

{article_list}

Total articles: {len(articles)}
Issues found so far: {len(issues)}

Provide:
1. Gaps: Important topics that seem to be missing given the existing content
2. Connections: Non-obvious connections between articles that could be explored
3. Questions: Interesting research questions that arise from the content
4. Suggestions: How to improve the overall structure and coverage

Be specific and actionable. Output as a markdown list."""

        analysis = ask(prompt, system=SYSTEM_PROMPT)
        suggestions.append(analysis)

    return {"issues": issues, "suggestions": suggestions}
