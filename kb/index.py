from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import yaml

from kb.config import CONCEPTS_DIR, INDEX_PATH, SOURCES_DIR, WIKI_DIR


def _read_frontmatter(path) -> dict:
    text = path.read_text()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = re.sub(r"\[\[([^\]]+)\]\]", r"\1", parts[1])
            try:
                return yaml.safe_load(fm) or {}
            except yaml.YAMLError:
                return {}
    return {}


def _count_words(path) -> int:
    text = path.read_text()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
    return len(text.split())


def _get_summary(path) -> str:
    """Extract first non-heading paragraph as a brief summary."""
    text = path.read_text()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
    for line in text.strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("-") and not line.startswith("*"):
            return line[:150].rstrip(".") + "..." if len(line) > 150 else line
    return ""


def rebuild_index() -> None:
    WIKI_DIR.mkdir(parents=True, exist_ok=True)

    lines = ["# Knowledge Base Index\n"]
    lines.append("Brief summaries of all articles for quick reference.\n")

    # Concepts
    concept_files = sorted(CONCEPTS_DIR.glob("*.md")) if CONCEPTS_DIR.exists() else []
    if concept_files:
        lines.append("## Concepts\n")
        for p in concept_files:
            meta = _read_frontmatter(p)
            title = meta.get("title", p.stem.replace("-", " ").title())
            tags = meta.get("tags", [])
            words = _count_words(p)
            summary = _get_summary(p)
            tag_str = f" ({', '.join(tags)})" if tags else ""
            lines.append(f"### [[concepts/{p.stem}|{title}]]")
            lines.append(f"*{words} words*{tag_str}")
            if summary:
                lines.append(f"{summary}")
            lines.append("")
        lines.append("")

    # Sources
    source_files = sorted(SOURCES_DIR.glob("*.md")) if SOURCES_DIR.exists() else []
    if source_files:
        lines.append("## Sources\n")
        for p in source_files:
            meta = _read_frontmatter(p)
            title = meta.get("title", p.stem.replace("-", " ").title())
            source_type = meta.get("source_type", "unknown")
            words = _count_words(p)
            summary = _get_summary(p)
            lines.append(f"### [[sources/{p.stem}|{title}]]")
            lines.append(f"*{words} words, {source_type}*")
            if summary:
                lines.append(f"{summary}")
            lines.append("")
        lines.append("")

    # Stats
    total_words = 0
    for d in [CONCEPTS_DIR, SOURCES_DIR]:
        if d.exists():
            for p in d.glob("*.md"):
                total_words += _count_words(p)

    lines.append("## Stats\n")
    lines.append(f"- **Concepts**: {len(concept_files)}")
    lines.append(f"- **Sources**: {len(source_files)}")
    lines.append(f"- **Total words**: {total_words:,}")
    lines.append("")

    INDEX_PATH.write_text("\n".join(lines))
    rebuild_backlinks()


def _slugify(name: str) -> str:
    """Convert a concept name or wikilink target to a filename slug."""
    slug = re.sub(r"[^\w\s-]", "", name.lower().strip())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug


def _strip_backlinks_section(text: str) -> str:
    """Remove an existing backlinks section from article text."""
    marker = "\n\n---\n\n## Backlinks\n\n"
    idx = text.find(marker)
    if idx != -1:
        return text[:idx]
    return text


def _article_paths() -> list[Path]:
    """Return all article .md files from concepts and sources directories."""
    paths: list[Path] = []
    for directory in [CONCEPTS_DIR, SOURCES_DIR]:
        if directory.exists():
            paths.extend(sorted(directory.glob("*.md")))
    return paths


def _extract_wikilinks(text: str) -> list[str]:
    """Extract wikilink targets from article text, ignoring display text after |."""
    return re.findall(r"\[\[([^\]|]+)", text)


def rebuild_backlinks() -> None:
    """Scan all articles for wikilinks and append a Backlinks section to each target."""
    articles = _article_paths()

    # Build a map from slug -> (relative_path_str, title) for every article
    slug_to_article: dict[str, tuple[str, str]] = {}
    for p in articles:
        meta = _read_frontmatter(p)
        title = meta.get("title", p.stem.replace("-", " ").title())
        rel = str(p.relative_to(WIKI_DIR))
        # Map by filename stem slug
        slug_to_article[p.stem.lower()] = (rel, title)
        # Also map by title slug so [[Vector Database]] matches vector-database.md
        slug_to_article[_slugify(title)] = (rel, title)

    # Build backlinks: target_rel_path -> list of (source_rel_path, source_title)
    backlinks: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for p in articles:
        meta = _read_frontmatter(p)
        source_title = meta.get("title", p.stem.replace("-", " ").title())
        source_rel = str(p.relative_to(WIKI_DIR))
        # Remove .md extension for the wikilink path
        source_link_path = source_rel.removesuffix(".md")

        text = p.read_text()
        text_no_backlinks = _strip_backlinks_section(text)
        links = _extract_wikilinks(text_no_backlinks)

        for link in links:
            # The link might be "concepts/foo" or just "Foo Bar"
            target_raw = link.strip()
            # Try direct slug match (handles "concepts/foo" style)
            slug = target_raw.lower()
            slug = re.sub(r"[^\w\s/-]", "", slug)
            slug = re.sub(r"[\s_]+", "-", slug).strip("-")

            # Try the full path slug first, then just the last segment
            candidates = [slug, slug.split("/")[-1], _slugify(target_raw)]
            matched = False
            for candidate in candidates:
                if candidate in slug_to_article:
                    target_rel, _ = slug_to_article[candidate]
                    if target_rel != source_rel:
                        existing = [s for s, _ in backlinks[target_rel]]
                        if source_rel not in existing:
                            backlinks[target_rel].append((source_link_path, source_title))
                    matched = True
                    break

    # Now write backlinks sections
    for p in articles:
        rel = str(p.relative_to(WIKI_DIR))
        text = p.read_text()
        clean_text = _strip_backlinks_section(text)

        if rel in backlinks and backlinks[rel]:
            entries = sorted(backlinks[rel], key=lambda x: x[1])
            lines = [f"- [[{path}|{title}]]" for path, title in entries]
            section = "\n\n---\n\n## Backlinks\n\n" + "\n".join(lines) + "\n"
            p.write_text(clean_text + section)
        elif clean_text != text:
            # Had a backlinks section before but now has zero backlinks; remove it
            p.write_text(clean_text)
