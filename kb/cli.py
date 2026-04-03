from __future__ import annotations

from pathlib import Path

import click

from kb.config import CONCEPTS_DIR, RAW_DIR, SOURCES_DIR, WIKI_DIR


@click.group()
def cli():
    """LLM-powered personal knowledge base."""


@cli.command()
@click.argument("source")
def ingest(source: str):
    """Ingest a file or URL into the knowledge base."""
    from kb.ingest import ingest_file, ingest_url

    if source.startswith(("http://", "https://")):
        click.echo(f"Fetching {source}...")
        dest = ingest_url(source)
    else:
        path = Path(source).expanduser().resolve()
        click.echo(f"Ingesting {path.name}...")
        dest = ingest_file(path)

    click.echo(f"Saved to {dest.relative_to(dest.parent.parent)}")


@cli.command()
@click.option("--force", is_flag=True, help="Recompile all sources, not just new ones.")
def compile(force: bool):
    """Compile raw sources into wiki articles."""
    from kb.compile import compile_kb

    click.echo("Compiling knowledge base...")
    result = compile_kb(force=force)
    click.echo(
        f"Done: {result['sources_compiled']} sources compiled, "
        f"{result['concepts_created']} concepts created."
    )


@cli.command()
@click.argument("question")
@click.option("-o", "--output", type=click.Path(), help="Write answer to a file.")
def query(question: str, output: str | None):
    """Ask a question against the knowledge base."""
    from kb.query import query_kb

    output_path = Path(output) if output else None
    answer = query_kb(question, output_file=output_path)
    click.echo(answer)


@cli.command()
@click.argument("term")
@click.option("-n", "--top", default=10, help="Number of results.")
def search(term: str, top: int):
    """Search the knowledge base."""
    from kb.search import search as search_fn

    results = search_fn(term, top_k=top)
    if not results:
        click.echo("No results found.")
        return

    for path, score, snippet in results:
        rel = path.relative_to(WIKI_DIR)
        click.echo(f"\n  {rel} (score: {score:.3f})")
        if snippet:
            click.echo(f"    {snippet}")


@cli.command()
@click.option("--no-llm", is_flag=True, help="Skip LLM-powered analysis (faster).")
def lint(no_llm: bool):
    """Run health checks on the knowledge base."""
    from kb.lint import lint_kb

    click.echo("Running health checks...")
    result = lint_kb(use_llm=not no_llm)

    if result["issues"]:
        click.echo(f"\nIssues ({len(result['issues'])}):")
        for issue in result["issues"]:
            click.echo(f"  - {issue}")
    else:
        click.echo("\nNo issues found.")

    if result["suggestions"]:
        click.echo("\nSuggestions:")
        for suggestion in result["suggestions"]:
            click.echo(suggestion)


@cli.command()
def status():
    """Show knowledge base statistics."""
    import json

    from kb.config import STATE_PATH

    raw_count = len(list(RAW_DIR.glob("*"))) if RAW_DIR.exists() else 0
    concept_count = len(list(CONCEPTS_DIR.glob("*.md"))) if CONCEPTS_DIR.exists() else 0
    source_count = len(list(SOURCES_DIR.glob("*.md"))) if SOURCES_DIR.exists() else 0

    total_words = 0
    for d in [CONCEPTS_DIR, SOURCES_DIR]:
        if d.exists():
            for p in d.glob("*.md"):
                total_words += len(p.read_text().split())

    compiled = 0
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text())
        compiled = sum(1 for s in state.get("sources", {}).values() if s.get("compiled"))

    click.echo("Knowledge Base Status")
    click.echo(f"  Raw sources:      {raw_count}")
    click.echo(f"  Compiled:         {compiled}")
    click.echo(f"  Source articles:   {source_count}")
    click.echo(f"  Concept articles:  {concept_count}")
    click.echo(f"  Total words:       {total_words:,}")
