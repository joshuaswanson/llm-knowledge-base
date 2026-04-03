from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from kb.ingest import _file_hash, _load_state, _save_state, _slugify, _write_raw_md


def _parse_twitter_json(data: list | dict) -> list[dict]:
    """Parse Twitter/X data export JSON into a list of bookmark dicts.

    Twitter's data export stores bookmarks as a list of tweet objects (or
    wrapped in a top-level key). Each tweet object contains at minimum an
    ``id`` and ``full_text`` (or ``text``).
    """
    # Twitter export may wrap bookmarks under a key
    if isinstance(data, dict):
        for key in ("data", "bookmarks"):
            if key in data:
                data = data[key]
                break
        # If still a dict with a single list value, unwrap it
        if isinstance(data, dict):
            lists = [v for v in data.values() if isinstance(v, list)]
            if len(lists) == 1:
                data = lists[0]

    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of tweet/bookmark objects")

    bookmarks: list[dict] = []
    for entry in data:
        # Twitter data exports sometimes nest inside {"tweet": {...}}
        tweet = entry.get("tweet", entry) if isinstance(entry, dict) else entry
        if not isinstance(tweet, dict):
            continue

        text = tweet.get("full_text") or tweet.get("text", "")
        author = (
            tweet.get("user", {}).get("screen_name")
            or tweet.get("user", {}).get("name")
            or tweet.get("core", {}).get("user_results", {}).get("result", {}).get("legacy", {}).get("screen_name")
            or "unknown"
        )
        tweet_id = str(tweet.get("id_str") or tweet.get("id", ""))
        created_at = tweet.get("created_at", "")

        # Extract URLs embedded in the tweet entities
        urls: list[str] = []
        for url_obj in tweet.get("entities", {}).get("urls", []):
            expanded = url_obj.get("expanded_url") or url_obj.get("url", "")
            if expanded:
                urls.append(expanded)

        source_url = f"https://x.com/i/status/{tweet_id}" if tweet_id else ""

        bookmarks.append({
            "text": text,
            "author": author,
            "tweet_id": tweet_id,
            "created_at": created_at,
            "urls": urls,
            "source_url": source_url,
        })

    return bookmarks


class _NetscapeBookmarkParser(HTMLParser):
    """Minimal parser for Netscape bookmark HTML format.

    This is the standard export format used by Chrome, Firefox, Safari, and
    most other browsers.
    """

    def __init__(self) -> None:
        super().__init__()
        self.bookmarks: list[dict] = []
        self._current_href: str | None = None
        self._current_text_parts: list[str] = []
        self._in_a = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            attr_dict = dict(attrs)
            self._current_href = attr_dict.get("href")
            self._current_text_parts = []
            self._in_a = True

    def handle_data(self, data: str) -> None:
        if self._in_a:
            self._current_text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._in_a:
            title = "".join(self._current_text_parts).strip()
            if self._current_href:
                self.bookmarks.append({
                    "title": title or self._current_href,
                    "url": self._current_href,
                })
            self._in_a = False
            self._current_href = None
            self._current_text_parts = []


def _parse_bookmark_html(html: str) -> list[dict]:
    """Parse Netscape bookmark HTML and return a list of {title, url} dicts."""
    parser = _NetscapeBookmarkParser()
    parser.feed(html)
    return parser.bookmarks


def import_twitter_bookmarks(file_path: Path) -> list[Path]:
    """Import bookmarks from a Twitter/X data export JSON file.

    Returns the list of created raw markdown file paths.
    """
    raw = file_path.read_text(errors="replace")
    data = json.loads(raw)
    bookmarks = _parse_twitter_json(data)

    if not bookmarks:
        raise ValueError(f"No bookmarks found in {file_path}")

    now = datetime.now(timezone.utc).isoformat()
    state = _load_state()
    created: list[Path] = []

    for bm in bookmarks:
        title = bm["text"][:100].strip() if bm["text"] else f"Tweet {bm['tweet_id']}"
        # Clean up the title for the filename
        slug = _slugify(title) or f"tweet-{bm['tweet_id']}"
        filename = f"{slug}.md"

        # Build body
        body_parts: list[str] = []
        if bm["text"]:
            body_parts.append(bm["text"])
        if bm["urls"]:
            body_parts.append("\n## Links\n")
            for url in bm["urls"]:
                body_parts.append(f"- {url}")

        body = "\n".join(body_parts)

        metadata = {
            "title": title,
            "source_url": bm["source_url"],
            "source_type": "bookmark",
            "platform": "twitter",
            "author": bm["author"],
            "tweet_date": bm["created_at"],
            "imported_at": now,
        }

        dest = _write_raw_md(filename, body, metadata)

        state["sources"][filename] = {
            "type": "bookmark",
            "platform": "twitter",
            "url": bm["source_url"],
            "title": title,
            "hash": _file_hash(dest),
            "imported_at": now,
            "compiled": False,
        }
        created.append(dest)

    _save_state(state)
    return created


def import_browser_bookmarks(file_path: Path) -> list[Path]:
    """Import bookmarks from a Netscape-format HTML bookmark export.

    Returns the list of created raw markdown file paths.
    """
    html = file_path.read_text(errors="replace")
    bookmarks = _parse_bookmark_html(html)

    if not bookmarks:
        raise ValueError(f"No bookmarks found in {file_path}")

    now = datetime.now(timezone.utc).isoformat()
    state = _load_state()
    created: list[Path] = []

    for bm in bookmarks:
        title = bm["title"]
        slug = _slugify(title) or "bookmark"
        filename = f"{slug}.md"

        # Avoid overwriting if slug collides
        if filename in state["sources"]:
            # Append a short hash of the URL to disambiguate
            url_suffix = _slugify(bm["url"].split("/")[-1] or bm["url"])[:20]
            filename = f"{slug}-{url_suffix}.md" if url_suffix else f"{slug}-dup.md"

        body = f"[{title}]({bm['url']})"

        metadata = {
            "title": title,
            "source_url": bm["url"],
            "source_type": "bookmark",
            "platform": "browser",
            "imported_at": now,
        }

        dest = _write_raw_md(filename, body, metadata)

        state["sources"][filename] = {
            "type": "bookmark",
            "platform": "browser",
            "url": bm["url"],
            "title": title,
            "hash": _file_hash(dest),
            "imported_at": now,
            "compiled": False,
        }
        created.append(dest)

    _save_state(state)
    return created


def import_bookmarks(file_path: Path) -> list[Path]:
    """Auto-detect format and import bookmarks from the given file.

    JSON files are treated as Twitter/X data exports. HTML files are treated
    as Netscape bookmark exports (Chrome, Firefox, Safari, etc.).
    """
    suffix = file_path.suffix.lower()

    if suffix == ".json":
        return import_twitter_bookmarks(file_path)
    if suffix in (".html", ".htm"):
        return import_browser_bookmarks(file_path)

    # Try to detect by content
    content_start = file_path.read_text(errors="replace")[:500].strip()
    if content_start.startswith(("{", "[")):
        return import_twitter_bookmarks(file_path)
    if re.match(r"<!DOCTYPE\s+NETSCAPE|<html|<dl", content_start, re.IGNORECASE):
        return import_browser_bookmarks(file_path)

    raise ValueError(
        f"Cannot detect bookmark format for {file_path.name}. "
        "Expected a .json (Twitter export) or .html (browser export) file."
    )
