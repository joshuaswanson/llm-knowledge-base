from __future__ import annotations

import re
from pathlib import Path

import click
import yaml

from kb.config import CONCEPTS_DIR, SOURCES_DIR, WIKI_DIR
from kb.llm import ask


def _read_frontmatter(path: Path) -> dict:
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


def _gather_stats() -> dict:
    concepts = []
    sources = []
    tags: dict[str, int] = {}
    links: dict[str, int] = {}

    for d, group in [(CONCEPTS_DIR, "concept"), (SOURCES_DIR, "source")]:
        if not d.exists():
            continue
        for p in d.glob("*.md"):
            text = p.read_text()
            meta = _read_frontmatter(p)
            title = meta.get("title", p.stem)
            words = len(text.split())
            entry = {"title": title, "words": words, "tags": meta.get("tags", []), "path": str(p)}

            if group == "concept":
                concepts.append(entry)
            else:
                sources.append(entry)

            for tag in meta.get("tags", []):
                tags[tag] = tags.get(tag, 0) + 1

            found_links = re.findall(r"\[\[([^\]|]+)", text)
            for link in found_links:
                name = link.split("/")[-1].strip()
                links[name] = links.get(name, 0) + 1

    return {
        "concepts": concepts,
        "sources": sources,
        "tags": tags,
        "links": links,
    }


def generate_chart(topic: str, output: Path | None = None) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    stats = _gather_stats()

    prompt = f"""\
Given these knowledge base statistics, generate Python matplotlib code to create
an informative visualization about: "{topic}"

Available data:
- {len(stats['concepts'])} concepts: {[c['title'] for c in stats['concepts'][:20]]}
- {len(stats['sources'])} sources: {[s['title'] for s in stats['sources'][:20]]}
- Tag frequency: {dict(sorted(stats['tags'].items(), key=lambda x: -x[1])[:20])}
- Most linked concepts: {dict(sorted(stats['links'].items(), key=lambda x: -x[1])[:20])}
- Word counts: concepts avg {sum(c['words'] for c in stats['concepts']) // max(len(stats['concepts']), 1)}, sources avg {sum(s['words'] for s in stats['sources']) // max(len(stats['sources']), 1)}

Generate ONLY Python code that:
1. Uses matplotlib.pyplot (already imported as plt)
2. Creates a single figure with plt.figure()
3. Calls plt.savefig(OUTPUT_PATH, dpi=150, bbox_inches='tight') at the end
4. Uses a clean style (plt.style.use('seaborn-v0_8-darkgrid') or similar)
5. Has a descriptive title
6. Do NOT call plt.show()

The variable OUTPUT_PATH will be defined before your code runs.
Output ONLY the Python code, no explanation."""

    code = ask(prompt, system="You are a data visualization expert. Output only valid Python code.")

    # Strip markdown code fences if present
    code = re.sub(r"```python\s*", "", code)
    code = re.sub(r"```\s*$", "", code)

    charts_dir = WIKI_DIR / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    if output is None:
        slug = re.sub(r"[^\w\s-]", "", topic.lower().strip())
        slug = re.sub(r"[\s_]+", "-", slug)[:60].strip("-")
        output = charts_dir / f"{slug}.png"

    output.parent.mkdir(parents=True, exist_ok=True)

    # Execute the generated code
    exec_globals = {"plt": plt, "OUTPUT_PATH": str(output)}
    try:
        exec(code, exec_globals)
    except Exception as e:
        click.echo(f"Chart generation failed: {e}")
        click.echo("Generated code:")
        click.echo(code)
        raise

    click.echo(f"Chart saved to {output}")
    return output
