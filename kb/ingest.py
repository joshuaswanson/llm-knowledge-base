import hashlib
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

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


def ingest_url(url: str) -> Path:
    if _is_youtube_url(url):
        return ingest_youtube(url)

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
