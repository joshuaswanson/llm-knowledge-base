import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import trafilatura
import yaml

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


def ingest_url(url: str) -> Path:
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
