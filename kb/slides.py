from __future__ import annotations

from pathlib import Path

import click

from kb.config import WIKI_DIR
from kb.llm import ask
from kb.search import search

SYSTEM_PROMPT = """\
You are a presentation designer. Create Marp-format markdown slides from wiki content.

Rules:
- Use Marp markdown format with `---` to separate slides
- Include a YAML header: `marp: true` and a theme
- First slide is a title slide
- Keep slides concise: max 5-7 bullet points per slide
- Use clear headings for each slide
- Include speaker notes with `<!-- notes -->` where helpful
- Use markdown formatting: bold, italic, code blocks where appropriate
- Aim for 8-15 slides depending on content depth
"""


def generate_slides(topic: str, output: Path | None = None) -> str:
    # Gather relevant wiki content
    results = search(topic, top_k=10)

    context_parts = []
    for path, score, _ in results:
        if score > 0.01:
            content = path.read_text()
            rel = path.relative_to(path.parent.parent)
            context_parts.append(f"## {rel}\n{content}")

    context = "\n\n---\n\n".join(context_parts)

    if not context.strip():
        return "Not enough content in the knowledge base to generate slides on this topic."

    prompt = f"""\
Create a Marp slide deck about: "{topic}"

Use the following wiki content as source material:

{context[:60000]}

Generate a complete Marp markdown presentation. Start with:
```
---
marp: true
theme: default
paginate: true
---
```

Then create slides covering the key points. Make it informative and well-structured."""

    slides = ask(prompt, system=SYSTEM_PROMPT)

    if output is None:
        slides_dir = WIKI_DIR / "slides"
        slides_dir.mkdir(parents=True, exist_ok=True)
        slug = topic.lower().replace(" ", "-")[:60]
        output = slides_dir / f"{slug}.md"

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(slides)
    click.echo(f"Slides written to {output}")

    return slides
