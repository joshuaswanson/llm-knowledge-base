from __future__ import annotations

from pathlib import Path

import click

from kb.config import INDEX_PATH
from kb.llm import ask
from kb.search import search

SYSTEM_PROMPT = """\
You are a knowledge base assistant. Answer questions using ONLY the provided wiki \
context. If the context doesn't contain enough information, say so clearly.

Rules:
- Cite your sources by referencing article titles
- Be precise and factual
- Use Obsidian wiki links [[Concept Name]] when referencing concepts
- If asked to create content (slides, summaries, etc.), format it as requested
"""


def _gather_context(question: str, max_chars: int = 80000) -> str:
    # Start with the index for overview
    parts = []
    if INDEX_PATH.exists():
        parts.append(f"## INDEX\n{INDEX_PATH.read_text()}")

    # Use search to find most relevant articles
    results = search(question, top_k=15)
    chars_used = sum(len(p) for p in parts)

    for path, score, _ in results:
        content = path.read_text()
        if chars_used + len(content) > max_chars:
            break
        rel = path.relative_to(path.parent.parent)
        parts.append(f"## {rel}\n{content}")
        chars_used += len(content)

    return "\n\n---\n\n".join(parts)


def query_kb(question: str, output_file: Path | None = None) -> str:
    context = _gather_context(question)

    if not context.strip():
        return "The knowledge base is empty. Ingest some sources first with `kb ingest`."

    prompt = f"""\
Answer the following question using the wiki context provided below.

QUESTION: {question}

WIKI CONTEXT:
{context}

Provide a thorough, well-structured answer. Reference specific articles where relevant."""

    answer = ask(prompt, system=SYSTEM_PROMPT)

    if output_file:
        output_file.write_text(answer)
        click.echo(f"Answer written to {output_file}")

    return answer
