import yaml

from kb.config import CONCEPTS_DIR, INDEX_PATH, SOURCES_DIR, WIKI_DIR


def _read_frontmatter(path) -> dict:
    import re
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


def rebuild_index() -> None:
    WIKI_DIR.mkdir(parents=True, exist_ok=True)

    lines = ["# Knowledge Base Index\n"]

    # Concepts
    concept_files = sorted(CONCEPTS_DIR.glob("*.md")) if CONCEPTS_DIR.exists() else []
    if concept_files:
        lines.append("## Concepts\n")
        for p in concept_files:
            meta = _read_frontmatter(p)
            title = meta.get("title", p.stem.replace("-", " ").title())
            tags = meta.get("tags", [])
            tag_str = f" `{'` `'.join(tags)}`" if tags else ""
            lines.append(f"- [[concepts/{p.stem}|{title}]]{tag_str}")
        lines.append("")

    # Sources
    source_files = sorted(SOURCES_DIR.glob("*.md")) if SOURCES_DIR.exists() else []
    if source_files:
        lines.append("## Sources\n")
        for p in source_files:
            meta = _read_frontmatter(p)
            title = meta.get("title", p.stem.replace("-", " ").title())
            lines.append(f"- [[sources/{p.stem}|{title}]]")
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
