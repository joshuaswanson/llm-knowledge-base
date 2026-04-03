from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx
import trafilatura
import yaml
import yt_dlp

from kb.config import RAW_DIR, STATE_PATH


def _load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"sources": {}}


def _save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2))


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:80].strip("-")


def _write_raw_md(filename: str, content: str, metadata: dict) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    frontmatter = yaml.dump(metadata, default_flow_style=False, allow_unicode=True).strip()
    full_content = f"---\n{frontmatter}\n---\n\n{content}"
    dest = RAW_DIR / filename
    dest.write_text(full_content)
    return dest


def _is_youtube_url(url: str) -> bool:
    host = urlparse(url).netloc.lower().replace("www.", "")
    return host in ("youtube.com", "youtu.be", "m.youtube.com")


def _strip_subtitle_timing(text: str) -> str:
    """Strip VTT/SRT timing cues and metadata, returning plain transcript text."""
    # Remove VTT header
    text = re.sub(r"^WEBVTT.*?\n\n", "", text, flags=re.DOTALL)
    # Remove SRT sequence numbers (standalone digits on a line)
    text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)
    # Remove timestamp lines (both VTT and SRT formats)
    text = re.sub(
        r"^\d{2}:\d{2}[:\.][\d.,]+ --> \d{2}:\d{2}[:\.][\d.,]+.*$",
        "",
        text,
        flags=re.MULTILINE,
    )
    # Remove VTT positioning tags like <c>, </c>, etc.
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse multiple blank lines and strip
    lines = []
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Deduplicate repeated caption lines (common in auto-generated subs)
        if line not in seen:
            seen.add(line)
            lines.append(line)
    return "\n".join(lines)


def ingest_youtube(url: str) -> Path:
    """Ingest a YouTube video transcript into the knowledge base."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en"],
            "subtitlesformat": "vtt",
            "outtmpl": str(tmp_path / "%(id)s"),
            "quiet": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        title = info.get("title", "Untitled Video")
        channel = info.get("channel") or info.get("uploader", "Unknown")
        upload_date_raw = info.get("upload_date", "")
        description = info.get("description", "")

        # Format upload date from YYYYMMDD to YYYY-MM-DD
        upload_date = upload_date_raw
        if upload_date_raw and len(upload_date_raw) == 8:
            upload_date = f"{upload_date_raw[:4]}-{upload_date_raw[4:6]}-{upload_date_raw[6:8]}"

        # Find the downloaded subtitle file
        transcript_text = ""
        sub_files = list(tmp_path.glob("*.vtt")) + list(tmp_path.glob("*.srt"))
        if sub_files:
            raw_subs = sub_files[0].read_text(errors="replace")
            transcript_text = _strip_subtitle_timing(raw_subs)

        if not transcript_text:
            raise ValueError(
                f"No English subtitles available for: {url}\n"
                "The video may not have captions enabled."
            )

        # Build the markdown body
        body_parts = []
        if description:
            body_parts.append(f"## Description\n\n{description.strip()}")
        body_parts.append(f"## Transcript\n\n{transcript_text}")
        body = "\n\n".join(body_parts)

        slug = _slugify(title)
        filename = f"{slug}.md"

        metadata = {
            "title": title,
            "source_url": url,
            "source_type": "youtube",
            "channel": channel,
            "upload_date": upload_date,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

        dest = _write_raw_md(filename, body, metadata)

    state = _load_state()
    state["sources"][filename] = {
        "type": "youtube",
        "url": url,
        "title": title,
        "channel": channel,
        "hash": _file_hash(dest),
        "ingested_at": metadata["ingested_at"],
        "compiled": False,
    }
    _save_state(state)

    return dest


def _is_rss_feed(content: str) -> bool:
    """Check whether raw text looks like an RSS or Atom feed."""
    # Only inspect the first 1000 chars to keep the check fast.
    head = content[:1000]
    return any(indicator in head for indicator in ("<rss", "<feed", "application/rss+xml", "<channel>"))


def _parse_rss_episodes(xml_text: str, max_episodes: int) -> tuple[str, list[dict]]:
    """Return (podcast_name, [episode_dicts]) from RSS XML.

    Each episode dict has keys: title, description, link, audio_url,
    pub_date, transcript_url.
    """
    root = ET.fromstring(xml_text)

    # Namespace map for common podcast extensions
    ns = {
        "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
        "podcast": "https://podcastindex.org/namespace/1.0",
        "atom": "http://www.w3.org/2005/Atom",
        "content": "http://purl.org/rss/1.0/modules/content/",
    }

    channel = root.find("channel")
    if channel is None:
        # Atom feeds use <feed> directly
        channel = root

    podcast_name = ""
    title_el = channel.find("title")
    if title_el is not None and title_el.text:
        podcast_name = title_el.text.strip()

    items = channel.findall("item")
    if not items:
        # Atom feeds use <entry> instead of <item>
        items = channel.findall("{http://www.w3.org/2005/Atom}entry")

    episodes: list[dict] = []
    for item in items[:max_episodes]:
        ep: dict = {
            "title": "",
            "description": "",
            "link": "",
            "audio_url": "",
            "pub_date": "",
            "transcript_url": "",
        }

        # Title
        t = item.find("title")
        if t is not None and t.text:
            ep["title"] = t.text.strip()

        # Link
        link_el = item.find("link")
        if link_el is not None:
            ep["link"] = (link_el.text or link_el.get("href", "")).strip()

        # Publication date
        pub = item.find("pubDate")
        if pub is not None and pub.text:
            ep["pub_date"] = pub.text.strip()

        # Description: prefer content:encoded, fall back to description
        content_encoded = item.find("content:encoded", ns)
        desc_el = item.find("description")
        if content_encoded is not None and content_encoded.text:
            ep["description"] = content_encoded.text.strip()
        elif desc_el is not None and desc_el.text:
            ep["description"] = desc_el.text.strip()

        # Audio URL from <enclosure>
        enclosure = item.find("enclosure")
        if enclosure is not None:
            enc_type = enclosure.get("type", "")
            if "audio" in enc_type or enclosure.get("url", "").split("?")[0].endswith(
                (".mp3", ".m4a", ".ogg", ".wav", ".opus")
            ):
                ep["audio_url"] = enclosure.get("url", "")

        # Transcript URL from <podcast:transcript>
        for transcript_el in item.findall("podcast:transcript", ns):
            url = transcript_el.get("url", "")
            if url:
                ep["transcript_url"] = url
                break

        episodes.append(ep)

    return podcast_name, episodes


def _fetch_transcript(transcript_url: str) -> str:
    """Download and clean a podcast transcript from a URL."""
    try:
        resp = httpx.get(transcript_url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPError:
        return ""

    text = resp.text
    content_type = resp.headers.get("content-type", "")

    # If it looks like VTT/SRT, strip timing cues
    if "vtt" in content_type or text.lstrip().startswith("WEBVTT") or transcript_url.endswith(".vtt"):
        return _strip_subtitle_timing(text)
    if "srt" in content_type or transcript_url.endswith(".srt"):
        return _strip_subtitle_timing(text)

    # JSON transcript (Podcasting 2.0 format)
    if "json" in content_type or transcript_url.endswith(".json"):
        try:
            data = json.loads(text)
            segments = data if isinstance(data, list) else data.get("segments", [])
            return "\n".join(s.get("body", s.get("text", "")) for s in segments if isinstance(s, dict))
        except (json.JSONDecodeError, TypeError):
            return text

    # Plain text or HTML: return as-is (HTML tags will be in show notes anyway)
    return text.strip()


def _strip_html_tags(text: str) -> str:
    """Remove HTML tags from text, keeping the inner content."""
    return re.sub(r"<[^>]+>", "", text)


def _parse_pub_date(date_str: str) -> str:
    """Try to parse an RSS pubDate into YYYY-MM-DD, or return the original."""
    # RSS dates are typically RFC 2822: "Mon, 01 Jan 2024 00:00:00 +0000"
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str.strip()


def ingest_podcast(rss_url: str, max_episodes: int = 5) -> list[Path]:
    """Ingest episodes from a podcast RSS feed into the knowledge base."""
    resp = httpx.get(rss_url, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    xml_text = resp.text

    podcast_name, episodes = _parse_rss_episodes(xml_text, max_episodes)

    if not episodes:
        raise ValueError(f"No episodes found in RSS feed: {rss_url}")

    state = _load_state()
    paths: list[Path] = []

    for ep in episodes:
        title = ep["title"] or "Untitled Episode"

        # Build body
        body_parts: list[str] = []

        if ep["description"]:
            cleaned = _strip_html_tags(ep["description"])
            body_parts.append(f"## Show Notes\n\n{cleaned.strip()}")

        # Try to fetch transcript
        if ep["transcript_url"]:
            transcript = _fetch_transcript(ep["transcript_url"])
            if transcript:
                body_parts.append(f"## Transcript\n\n{transcript.strip()}")

        if not body_parts:
            body_parts.append("*No show notes or transcript available.*")

        body = "\n\n".join(body_parts)

        episode_date = _parse_pub_date(ep["pub_date"]) if ep["pub_date"] else ""

        slug = _slugify(title)
        filename = f"{slug}.md"

        metadata: dict = {
            "title": title,
            "source_url": ep["link"] or rss_url,
            "source_type": "podcast",
            "podcast_name": podcast_name,
            "episode_date": episode_date,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

        dest = _write_raw_md(filename, body, metadata)
        paths.append(dest)

        state["sources"][filename] = {
            "type": "podcast",
            "url": ep["link"] or rss_url,
            "title": title,
            "podcast_name": podcast_name,
            "hash": _file_hash(dest),
            "ingested_at": metadata["ingested_at"],
            "compiled": False,
        }

    _save_state(state)
    return paths


def ingest_url(url: str) -> Path | list[Path]:
    if _is_youtube_url(url):
        return ingest_youtube(url)

    # Check if the URL points to an RSS/Atom feed
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "xml" in content_type or "rss" in content_type or "atom" in content_type or _is_rss_feed(resp.text):
            return ingest_podcast(url)
    except httpx.HTTPError:
        pass  # Fall through to trafilatura

    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError(f"Failed to fetch URL: {url}")

    text = trafilatura.extract(
        downloaded,
        include_links=True,
        include_images=True,
        include_tables=True,
        output_format="txt",
    )
    if not text:
        raise ValueError(f"Failed to extract content from: {url}")

    metadata_raw = trafilatura.extract(downloaded, output_format="xmltei", include_links=True)
    title = ""
    if metadata_raw:
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", metadata_raw)
        if title_match:
            title = title_match.group(1).strip()

    if not title:
        domain = urlparse(url).netloc.replace("www.", "")
        title = f"Article from {domain}"

    slug = _slugify(title)
    filename = f"{slug}.md"

    metadata = {
        "title": title,
        "source_url": url,
        "source_type": "url",
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }

    dest = _write_raw_md(filename, text, metadata)

    state = _load_state()
    state["sources"][filename] = {
        "type": "url",
        "url": url,
        "title": title,
        "hash": _file_hash(dest),
        "ingested_at": metadata["ingested_at"],
        "compiled": False,
    }
    _save_state(state)

    return dest


def ingest_file(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    title = path.stem.replace("-", " ").replace("_", " ").title()

    if path.suffix == ".md":
        dest = RAW_DIR / path.name
        shutil.copy2(path, dest)
        # Ensure frontmatter exists
        content = dest.read_text()
        if not content.startswith("---"):
            metadata = {
                "title": title,
                "source_type": "file",
                "source_path": str(path),
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }
            frontmatter = yaml.dump(metadata, default_flow_style=False, allow_unicode=True).strip()
            dest.write_text(f"---\n{frontmatter}\n---\n\n{content}")
    else:
        content = path.read_text(errors="replace")
        metadata = {
            "title": path.stem.replace("-", " ").replace("_", " ").title(),
            "source_type": "file",
            "source_path": str(path),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        dest = _write_raw_md(f"{_slugify(path.stem)}.md", content, metadata)

    state = _load_state()
    filename = dest.name
    state["sources"][filename] = {
        "type": "file",
        "original_path": str(path),
        "title": title,
        "hash": _file_hash(dest),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "compiled": False,
    }
    _save_state(state)

    return dest
