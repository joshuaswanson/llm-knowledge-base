from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx
import trafilatura
import yaml
import yt_dlp

from kb.config import IMAGES_DIR, RAW_DIR, STATE_PATH

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


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


def _download_image(img_url: str, base_url: str = "") -> str | None:
    """Download an image from *img_url* into IMAGES_DIR.

    Returns the local filename on success, or ``None`` on failure.
    """
    # Resolve relative URLs
    if img_url.startswith("//"):
        img_url = "https:" + img_url
    elif img_url.startswith("/") and base_url:
        parsed = urlparse(base_url)
        img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
    elif not img_url.startswith(("http://", "https://")):
        return None

    # Derive a filename from the URL path
    parsed_img = urlparse(img_url)
    url_path = parsed_img.path.rstrip("/")
    basename = Path(url_path).name if url_path else ""
    if not basename:
        return None

    # Only keep recognised image extensions
    suffix = Path(basename).suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        return None

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # Deduplicate: hash the URL to create a unique prefix
    url_hash = hashlib.sha256(img_url.encode()).hexdigest()[:8]
    local_name = f"{url_hash}-{basename}"
    dest = IMAGES_DIR / local_name
    if dest.exists():
        return local_name

    try:
        resp = httpx.get(img_url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return local_name
    except httpx.HTTPError:
        return None


def _download_images_and_rewrite(text: str, source_url: str) -> str:
    """Find image references in *text*, download them, and rewrite paths."""

    def _replace_md_image(m: re.Match) -> str:
        alt = m.group(1)
        img_url = m.group(2)
        local = _download_image(img_url, base_url=source_url)
        if local:
            return f"![{alt}](images/{local})"
        return m.group(0)

    # Markdown image syntax: ![alt](url)
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _replace_md_image, text)

    # HTML <img> tags
    def _replace_html_img(m: re.Match) -> str:
        tag = m.group(0)
        src_match = re.search(r'src=["\']([^"\']+)["\']', tag)
        if not src_match:
            return tag
        img_url = src_match.group(1)
        local = _download_image(img_url, base_url=source_url)
        if local:
            alt_match = re.search(r'alt=["\']([^"\']*)["\']', tag)
            alt = alt_match.group(1) if alt_match else ""
            return f"![{alt}](images/{local})"
        return tag

    text = re.sub(r"<img\s[^>]+>", _replace_html_img, text, flags=re.IGNORECASE)
    return text


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


def _is_repo_url(url: str) -> bool:
    """Check whether a URL points to a GitHub or GitLab repository."""
    host = urlparse(url).netloc.lower().replace("www.", "")
    if host not in ("github.com", "gitlab.com"):
        return False
    # Repo URLs have at least /owner/repo in the path
    parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
    if len(parts) < 2:
        return False
    # Exclude URLs that go deeper into specific resources like /issues, /pull, /blob
    if len(parts) > 2 and parts[2] in (
        "issues", "pull", "pulls", "blob", "tree", "commit", "commits",
        "actions", "releases", "wiki", "settings", "compare",
    ):
        return False
    return True


def _build_file_tree(root: Path, max_depth: int = 3, prefix: str = "") -> str:
    """Build an indented file tree string, limited to max_depth levels."""
    if max_depth < 0:
        return ""
    try:
        entries = sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        return ""
    lines: list[str] = []
    skip = {".git", "__pycache__", "node_modules", ".tox", ".mypy_cache", ".pytest_cache", "venv", ".venv"}
    filtered = [e for e in entries if e.name not in skip]
    for i, entry in enumerate(filtered):
        connector = "--- " if i == len(filtered) - 1 else "|-- "
        lines.append(f"{prefix}{connector}{entry.name}")
        if entry.is_dir() and max_depth > 0:
            extension = "    " if i == len(filtered) - 1 else "|   "
            subtree = _build_file_tree(entry, max_depth - 1, prefix + extension)
            if subtree:
                lines.append(subtree)
    return "\n".join(lines)


def _detect_language(root: Path) -> str:
    """Guess the primary programming language from file extensions."""
    ext_counts: Counter[str] = Counter()
    lang_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".jsx": "JavaScript", ".tsx": "TypeScript", ".rs": "Rust",
        ".go": "Go", ".java": "Java", ".c": "C", ".cpp": "C++",
        ".h": "C", ".hpp": "C++", ".rb": "Ruby", ".swift": "Swift",
        ".kt": "Kotlin", ".scala": "Scala", ".cs": "C#",
        ".php": "PHP", ".lua": "Lua", ".zig": "Zig", ".jl": "Julia",
        ".r": "R", ".R": "R",
    }
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in lang_map:
            ext_counts[path.suffix] += 1
    if not ext_counts:
        return "Unknown"
    top_ext = ext_counts.most_common(1)[0][0]
    return lang_map.get(top_ext, "Unknown")


def _fetch_github_stars(owner: str, repo: str) -> int | None:
    """Try to fetch star count from the GitHub API. Returns None on failure."""
    try:
        resp = httpx.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("stargazers_count")
    except httpx.HTTPError:
        pass
    return None


def ingest_repo(repo_url: str) -> Path:
    """Ingest a git repository into the knowledge base.

    Clones the repo (shallow, depth=1), reads README and key metadata files,
    builds a directory tree, and saves a markdown summary to raw/.
    """
    parsed = urlparse(repo_url)
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(path_parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from URL: {repo_url}")
    owner, repo_name = path_parts[0], path_parts[1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    with tempfile.TemporaryDirectory() as tmp_dir:
        clone_dest = Path(tmp_dir) / repo_name
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(clone_dest)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {result.stderr.strip()}")

        body_parts: list[str] = []

        # README
        readme_path = None
        for name in ("README.md", "readme.md", "Readme.md", "README.rst", "README.txt", "README"):
            candidate = clone_dest / name
            if candidate.exists():
                readme_path = candidate
                break
        if readme_path:
            readme_text = readme_path.read_text(errors="replace")
            body_parts.append(f"## README\n\n{readme_text.strip()}")

        # Directory tree
        tree = _build_file_tree(clone_dest, max_depth=3)
        if tree:
            body_parts.append(f"## Directory Structure\n\n```\n{repo_name}/\n{tree}\n```")

        # Key metadata files
        metadata_files = [
            "setup.py", "pyproject.toml", "package.json", "Cargo.toml",
            "go.mod", "Makefile", "CMakeLists.txt",
        ]
        root_md_files = [
            p.name for p in clone_dest.iterdir()
            if p.is_file() and p.suffix == ".md" and p.name.lower() != "readme.md"
        ]
        files_to_read = metadata_files + sorted(root_md_files)

        for fname in files_to_read:
            fpath = clone_dest / fname
            if fpath.exists() and fpath.is_file():
                try:
                    content = fpath.read_text(errors="replace")
                    if len(content) > 5000:
                        content = content[:5000] + "\n\n[... truncated]"
                    body_parts.append(f"## {fname}\n\n```\n{content.strip()}\n```")
                except Exception:
                    pass

        language = _detect_language(clone_dest)

    if not body_parts:
        body_parts.append("*No readable content found in the repository.*")

    body = "\n\n".join(body_parts)
    slug = _slugify(repo_name)
    filename = f"{slug}.md"

    metadata: dict = {
        "title": repo_name,
        "source_url": repo_url,
        "source_type": "repo",
        "language": language,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }

    host = parsed.netloc.lower().replace("www.", "")
    if host == "github.com":
        stars = _fetch_github_stars(owner, repo_name)
        if stars is not None:
            metadata["stars"] = stars

    dest = _write_raw_md(filename, body, metadata)

    state = _load_state()
    state["sources"][filename] = {
        "type": "repo",
        "url": repo_url,
        "title": repo_name,
        "language": language,
        "hash": _file_hash(dest),
        "ingested_at": metadata["ingested_at"],
        "compiled": False,
    }
    _save_state(state)

    return dest


def _guess_csv_dtype(values: list[str]) -> str:
    """Guess the data type of a CSV column from sample values."""
    if not values:
        return "unknown"
    int_count = 0
    float_count = 0
    bool_count = 0
    for v in values:
        v_stripped = v.strip()
        if v_stripped.lower() in ("true", "false"):
            bool_count += 1
            continue
        try:
            int(v_stripped)
            int_count += 1
            continue
        except ValueError:
            pass
        try:
            float(v_stripped)
            float_count += 1
            continue
        except ValueError:
            pass
    total = len(values)
    if bool_count == total:
        return "boolean"
    if int_count == total:
        return "integer"
    if (int_count + float_count) == total:
        return "numeric"
    return "string"


def ingest_dataset(path: Path) -> Path:
    """Ingest a CSV or JSON dataset into the knowledge base.

    Reads schema information and sample data, then saves a markdown summary
    to raw/.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in (".csv", ".json"):
        raise ValueError(f"Unsupported dataset format: {suffix} (expected .csv or .json)")

    title = path.stem.replace("-", " ").replace("_", " ").title()
    body_parts: list[str] = []

    if suffix == ".csv":
        text = path.read_text(errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            raise ValueError(f"CSV file is empty: {path}")

        header = rows[0]
        data_rows = rows[1:]
        num_rows = len(data_rows)
        num_cols = len(header)

        body_parts.append(f"## Schema\n\n- **Rows:** {num_rows:,}\n- **Columns:** {num_cols}")

        col_info_lines = ["| Column | Sample Values | Inferred Type |", "| --- | --- | --- |"]
        for col_idx, col_name in enumerate(header):
            values = [r[col_idx] for r in data_rows[:20] if col_idx < len(r) and r[col_idx]]
            dtype = _guess_csv_dtype(values)
            sample = ", ".join(values[:3]) if values else "(empty)"
            if len(sample) > 60:
                sample = sample[:60] + "..."
            col_info_lines.append(f"| {col_name} | {sample} | {dtype} |")
        body_parts.append("## Columns\n\n" + "\n".join(col_info_lines))

        sample_rows = data_rows[:5]
        if sample_rows:
            table_lines = ["| " + " | ".join(header) + " |"]
            table_lines.append("| " + " | ".join("---" for _ in header) + " |")
            for row in sample_rows:
                padded = row + [""] * (len(header) - len(row))
                cells = [c[:50] + "..." if len(c) > 50 else c for c in padded[:len(header)]]
                table_lines.append("| " + " | ".join(cells) + " |")
            body_parts.append("## Sample Data (first 5 rows)\n\n" + "\n".join(table_lines))

        fm_metadata: dict = {
            "title": title,
            "source_type": "dataset",
            "source_path": str(path),
            "format": "csv",
            "rows": num_rows,
            "columns": num_cols,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

    else:  # JSON
        text = path.read_text(errors="replace")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}") from e

        if isinstance(data, list):
            num_records = len(data)
            body_parts.append(f"## Structure\n\n- **Type:** Array of {num_records:,} records")

            if num_records > 0 and isinstance(data[0], dict):
                keys = list(data[0].keys())
                body_parts.append(f"- **Fields:** {', '.join(keys)}")

                sample = data[:3]
                sample_text = json.dumps(sample, indent=2, default=str)
                if len(sample_text) > 3000:
                    sample_text = sample_text[:3000] + "\n... (truncated)"
                body_parts.append(f"## Sample Records\n\n```json\n{sample_text}\n```")
            elif num_records > 0:
                sample = data[:5]
                sample_text = json.dumps(sample, indent=2, default=str)
                body_parts.append(f"## Sample Values\n\n```json\n{sample_text}\n```")

            fm_metadata = {
                "title": title,
                "source_type": "dataset",
                "source_path": str(path),
                "format": "json",
                "rows": num_records,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }

        elif isinstance(data, dict):
            top_keys = list(data.keys())
            body_parts.append(f"## Structure\n\n- **Type:** Object with {len(top_keys)} top-level keys")
            body_parts.append(f"- **Keys:** {', '.join(top_keys)}")

            for key in top_keys:
                val = data[key]
                if isinstance(val, list):
                    body_parts.append(f"- **`{key}`:** Array of {len(val):,} items")

            sample_text = json.dumps(data, indent=2, default=str)
            if len(sample_text) > 3000:
                sample_text = sample_text[:3000] + "\n... (truncated)"
            body_parts.append(f"## Content Preview\n\n```json\n{sample_text}\n```")

            fm_metadata = {
                "title": title,
                "source_type": "dataset",
                "source_path": str(path),
                "format": "json",
                "columns": len(top_keys),
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }

        else:
            raise ValueError(f"Unexpected JSON root type: {type(data).__name__}")

    body = "\n\n".join(body_parts)
    slug = _slugify(path.stem)
    filename = f"{slug}.md"

    dest = _write_raw_md(filename, body, fm_metadata)

    state = _load_state()
    state["sources"][filename] = {
        "type": "dataset",
        "original_path": str(path),
        "title": title,
        "format": suffix.lstrip("."),
        "hash": _file_hash(dest),
        "ingested_at": fm_metadata["ingested_at"],
        "compiled": False,
    }
    _save_state(state)

    return dest


def ingest_url(url: str) -> Path | list[Path]:
    if _is_youtube_url(url):
        return ingest_youtube(url)

    if _is_repo_url(url):
        return ingest_repo(url)

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

    # Download images referenced in the article and rewrite paths
    text = _download_images_and_rewrite(text, url)

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

    # Route dataset files to ingest_dataset
    if path.suffix.lower() in (".csv", ".json"):
        return ingest_dataset(path)

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    title = path.stem.replace("-", " ").replace("_", " ").title()

    # Handle image files
    if path.suffix.lower() in IMAGE_EXTENSIONS:
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        img_dest = IMAGES_DIR / path.name
        shutil.copy2(path, img_dest)

        metadata = {
            "title": title,
            "source_type": "image",
            "source_path": str(path),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        body = f"![](images/{path.name})"
        dest = _write_raw_md(f"{_slugify(path.stem)}.md", body, metadata)

        state = _load_state()
        filename = dest.name
        state["sources"][filename] = {
            "type": "image",
            "original_path": str(path),
            "title": title,
            "hash": _file_hash(img_dest),
            "ingested_at": metadata["ingested_at"],
            "compiled": False,
        }
        _save_state(state)
        return dest

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
