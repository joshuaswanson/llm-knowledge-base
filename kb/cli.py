from __future__ import annotations

from pathlib import Path

import click

from kb.config import CONCEPTS_DIR, RAW_DIR, SOURCES_DIR, WIKI_DIR


@click.group()
def cli():
    """LLM-powered personal knowledge base."""


@cli.command()
@click.argument("sources", nargs=-1, required=True)
@click.option("--compile", "auto_compile", is_flag=True, help="Auto-compile after ingesting.")
def ingest(sources: tuple[str, ...], auto_compile: bool):
    """Ingest files or URLs into the knowledge base.

    Accepts multiple sources at once. URLs are auto-detected.
    YouTube URLs, RSS feeds, and GitHub repos are handled specially.
    """
    from kb.ingest import ingest_file, ingest_url

    for source in sources:
        if source.startswith(("http://", "https://")):
            click.echo(f"Fetching {source}...")
            dest = ingest_url(source)
        else:
            path = Path(source).expanduser().resolve()
            click.echo(f"Ingesting {path.name}...")
            dest = ingest_file(path)
        if isinstance(dest, list):
            for p in dest:
                click.echo(f"  Saved to {p.relative_to(p.parent.parent)}")
        else:
            click.echo(f"  Saved to {dest.relative_to(dest.parent.parent)}")

    if auto_compile:
        from kb.compile import compile_kb

        click.echo("\nCompiling...")
        result = compile_kb()
        click.echo(
            f"Done: {result['sources_compiled']} sources compiled, "
            f"{result['concepts_created']} concepts created."
        )


@cli.command("ingest-podcast")
@click.argument("rss_url")
@click.option("--max-episodes", default=5, show_default=True, help="Maximum number of episodes to ingest.")
def ingest_podcast(rss_url: str, max_episodes: int):
    """Ingest episodes from a podcast RSS feed.

    Fetches the RSS feed, extracts episode metadata, and saves
    show notes and transcripts (when available) to the knowledge base.
    """
    from kb.ingest import ingest_podcast as _ingest_podcast

    click.echo(f"Fetching podcast feed: {rss_url}")
    paths = _ingest_podcast(rss_url, max_episodes=max_episodes)
    click.echo(f"Ingested {len(paths)} episode(s):")
    for p in paths:
        click.echo(f"  {p.relative_to(p.parent.parent)}")


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
@click.option("--save", is_flag=True, help="Save answer back into the wiki.")
def query(question: str, output: str | None, save: bool):
    """Ask a question against the knowledge base."""
    from kb.query import query_kb

    output_path = Path(output) if output else None
    answer = query_kb(question, output_file=output_path, save_to_wiki=save)
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
@click.argument("topic")
@click.option("-o", "--output", type=click.Path(), help="Output file path.")
def slides(topic: str, output: str | None):
    """Generate a Marp slide deck from wiki content."""
    from kb.slides import generate_slides

    output_path = Path(output) if output else None
    generate_slides(topic, output=output_path)


@cli.command()
@click.argument("topic")
@click.option("-o", "--output", type=click.Path(), help="Output file path.")
def chart(topic: str, output: str | None):
    """Generate a matplotlib chart from wiki data."""
    from kb.chart import generate_chart

    output_path = Path(output) if output else None
    generate_chart(topic, output=output_path)


@cli.command("import-bookmarks")
@click.argument("file", type=click.Path(exists=True))
def import_bookmarks_cmd(file: str):
    """Import bookmarks from a Twitter/X export (JSON) or browser export (HTML).

    Accepts the standard Netscape bookmark HTML format exported by
    Chrome, Firefox, and Safari, as well as the JSON format from
    Twitter's data export.
    """
    from kb.import_bookmarks import import_bookmarks

    path = Path(file).expanduser().resolve()
    click.echo(f"Importing bookmarks from {path.name}...")
    created = import_bookmarks(path)
    click.echo(f"Imported {len(created)} bookmark(s) into raw/")
    for dest in created:
        click.echo(f"  {dest.name}")


@cli.command()
def status():
    """Show knowledge base statistics."""
    import json

    from kb.config import STATE_PATH

    raw_count = len(list(RAW_DIR.glob("*"))) if RAW_DIR.exists() else 0
    concept_count = len(list(CONCEPTS_DIR.glob("*.md"))) if CONCEPTS_DIR.exists() else 0
    source_count = len(list(SOURCES_DIR.glob("*.md"))) if SOURCES_DIR.exists() else 0

    queries_dir = WIKI_DIR / "queries"
    query_count = len(list(queries_dir.glob("*.md"))) if queries_dir.exists() else 0

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
    click.echo(f"  Raw sources:       {raw_count}")
    click.echo(f"  Compiled:          {compiled}")
    click.echo(f"  Source articles:    {source_count}")
    click.echo(f"  Concept articles:   {concept_count}")
    click.echo(f"  Saved queries:      {query_count}")
    click.echo(f"  Total words:        {total_words:,}")


@cli.command()
@click.option("--server", default="http://localhost:3000", help="Server URL for the bookmarklet.")
def bookmarklet(server: str):
    """Print the bookmarklet JavaScript for browser integration."""
    server = server.rstrip("/")
    js = (
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
        ".then(function(){n.style.background='#16a34a';n.textContent='Saved to KB';"
        "setTimeout(function(){n.style.opacity='0';setTimeout(function(){n.remove()},400)},2000)})"
        ".catch(function(e){n.style.background='#dc2626';n.textContent='Failed: '+e.message;"
        "setTimeout(function(){n.style.opacity='0';setTimeout(function(){n.remove()},400)},3000)})"
        "})())"
    )
    click.echo("Bookmarklet JavaScript")
    click.echo("=" * 60)
    click.echo()
    click.echo(js)
    click.echo()
    click.echo("=" * 60)
    click.echo()
    click.echo("How to install:")
    click.echo("  1. Create a new bookmark in your browser.")
    click.echo("  2. Set the name to 'Save to KB'.")
    click.echo("  3. Paste the JavaScript above as the URL.")
    click.echo("  4. Click the bookmark on any page to ingest it.")


@cli.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option("--compile-after", is_flag=True, help="Run compile after ingesting.")
def watch(directory: str, compile_after: bool):
    """Watch a directory and ingest new files automatically."""
    import time

    from kb.ingest import ingest_file

    watch_dir = Path(directory).resolve()
    seen: set[str] = set()

    # Index existing files
    for p in watch_dir.iterdir():
        seen.add(str(p))

    click.echo(f"Watching {watch_dir} for new files... (Ctrl+C to stop)")

    try:
        while True:
            for p in watch_dir.iterdir():
                if str(p) not in seen and p.is_file():
                    seen.add(str(p))
                    click.echo(f"New file: {p.name}")
                    try:
                        dest = ingest_file(p)
                        click.echo(f"  Ingested to {dest.name}")
                        if compile_after:
                            from kb.compile import compile_kb
                            compile_kb()
                    except Exception as e:
                        click.echo(f"  Error: {e}")
            time.sleep(2)
    except KeyboardInterrupt:
        click.echo("\nStopped watching.")
