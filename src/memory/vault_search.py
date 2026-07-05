"""In-memory vault index — parses Markdown notes and serves relevance search.

No embedding model or external search engine is used (see research.md
Decision 2): a lazy, mtime-based rebuild keeps a plain Python in-memory index
fast enough for vaults up to 10,000 notes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from src.memory.audit import get_logger

_log = get_logger("memory.vault_search")

_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
_TAG_BOOST = 5.0


@dataclass
class VaultNote:
    """A single parsed Markdown file inside the vault."""

    path: Path
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    mtime: float = 0.0


@dataclass
class VaultSearchResult:
    """A note returned by VaultIndex.search(), ranked by relevance."""

    note: VaultNote
    score: float
    excerpt: str


def _tokenize(text: str) -> set[str]:
    return {tok for tok in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(tok) > 2}


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split leading YAML frontmatter (--- ... ---) from the body."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    _, raw_frontmatter, body = parts
    try:
        frontmatter = yaml.safe_load(raw_frontmatter) or {}
    except yaml.YAMLError:
        frontmatter = {}
    if not isinstance(frontmatter, dict):
        frontmatter = {}
    return frontmatter, body.lstrip("\n")


def _parse_note(path: Path) -> VaultNote:
    raw = path.read_text(encoding="utf-8")
    frontmatter, body = _parse_frontmatter(raw)

    heading_match = _HEADING_RE.search(body)
    title = heading_match.group(1).strip() if heading_match else path.stem

    tags = frontmatter.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]

    links = _WIKILINK_RE.findall(body)

    return VaultNote(
        path=path,
        title=title,
        content=body,
        tags=list(tags),
        links=list(links),
        mtime=path.stat().st_mtime,
    )


def _excerpt(content: str, max_len: int = 240) -> str:
    text = " ".join(content.split())
    return text[:max_len]


class VaultIndex:
    """In-memory index of a vault's Markdown notes, with lazy mtime-based rebuild."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._notes: dict[Path, VaultNote] = {}

    def refresh(self) -> None:
        """Re-parse any new or changed .md files; drop notes for deleted files."""
        current_paths: set[Path] = set()
        for md_path in self._root.rglob("*.md"):
            current_paths.add(md_path)
            existing = self._notes.get(md_path)
            mtime = md_path.stat().st_mtime
            if existing is not None and existing.mtime == mtime:
                continue
            self._notes[md_path] = _parse_note(md_path)

        for stale_path in list(self._notes):
            if stale_path not in current_paths:
                del self._notes[stale_path]

    def notes(self) -> list[VaultNote]:
        return list(self._notes.values())

    def search(self, query: str) -> list[VaultSearchResult]:
        """Return notes ranked by token-overlap score, boosted by tag matches."""
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        results: list[VaultSearchResult] = []
        for note in self._notes.values():
            content_tokens = _tokenize(note.content) | _tokenize(note.title)
            overlap = query_tokens & content_tokens
            if not overlap:
                continue
            score = float(len(overlap))
            tag_tokens = _tokenize(" ".join(note.tags))
            score += _TAG_BOOST * len(query_tokens & tag_tokens)
            results.append(VaultSearchResult(note=note, score=score, excerpt=_excerpt(note.content)))

        results.sort(key=lambda r: r.score, reverse=True)
        _log.debug("vault_search", query=query, result_count=len(results))
        return results
