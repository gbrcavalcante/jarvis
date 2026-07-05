"""Tests for VaultIndex — parsing and relevance search (US2)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest


def _write_note(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# T026 — VaultIndex parses title, frontmatter tags, and wiki-links
# ---------------------------------------------------------------------------

def test_vault_index_parses_note_title_tags_and_links(tmp_path: Path) -> None:
    from src.memory.vault_search import VaultIndex

    note_path = tmp_path / "jarvis.md"
    _write_note(note_path, """---
tags: [project, voice]
---
# jarvis

JARVIS is a voice assistant. See [[voice-ui]] and [[settings|Settings Guide]].
""")

    index = VaultIndex(tmp_path)
    index.refresh()
    notes = index.notes()

    assert len(notes) == 1
    note = notes[0]
    assert note.title == "jarvis"
    assert "voice assistant" in note.content
    assert set(note.tags) == {"project", "voice"}
    assert set(note.links) == {"voice-ui", "settings"}


def test_vault_index_uses_filename_when_no_heading(tmp_path: Path) -> None:
    from src.memory.vault_search import VaultIndex

    _write_note(tmp_path / "untitled-note.md", "Just some content, no heading.")

    index = VaultIndex(tmp_path)
    index.refresh()
    notes = index.notes()

    assert notes[0].title == "untitled-note"


def test_vault_index_ignores_non_markdown_files(tmp_path: Path) -> None:
    from src.memory.vault_search import VaultIndex

    _write_note(tmp_path / "note.md", "# note\ncontent")
    (tmp_path / "image.png").write_bytes(b"\x89PNG")

    index = VaultIndex(tmp_path)
    index.refresh()

    assert len(index.notes()) == 1


# ---------------------------------------------------------------------------
# T027 — search() ranks by token-overlap score, boosted by tag matches
# ---------------------------------------------------------------------------

def test_vault_index_search_ranks_by_relevance(tmp_path: Path) -> None:
    from src.memory.vault_search import VaultIndex

    _write_note(tmp_path / "jarvis.md", "# jarvis\n\nJARVIS is a voice-first AI assistant.")
    _write_note(tmp_path / "unrelated.md", "# unrelated\n\nA note about gardening.")

    index = VaultIndex(tmp_path)
    index.refresh()
    results = index.search("Tell me about JARVIS the voice assistant")

    assert len(results) >= 1
    assert results[0].note.title == "jarvis"
    assert results[0].score > 0


def test_vault_index_search_boosts_tag_matches(tmp_path: Path) -> None:
    from src.memory.vault_search import VaultIndex

    _write_note(tmp_path / "a.md", """---
tags: [voice]
---
# a

Some generic overlapping words here about assistant.
""")
    _write_note(tmp_path / "b.md", "# b\n\nSome generic overlapping words here about assistant.")

    index = VaultIndex(tmp_path)
    index.refresh()
    results = index.search("voice assistant")

    by_title = {r.note.title: r.score for r in results}
    assert by_title["a"] > by_title["b"]


# ---------------------------------------------------------------------------
# T028 — lazy rebuild: only re-parses files whose mtime changed
# ---------------------------------------------------------------------------

def test_vault_index_lazy_rebuild_skips_unchanged_files(tmp_path: Path) -> None:
    from src.memory.vault_search import VaultIndex

    note_path = tmp_path / "note.md"
    _write_note(note_path, "# note\ncontent")

    index = VaultIndex(tmp_path)
    index.refresh()
    first_notes = index.notes()

    # No filesystem change — refresh() should not reparse (same object identity)
    index.refresh()
    second_notes = index.notes()

    assert first_notes[0] is second_notes[0]


def test_vault_index_lazy_rebuild_reparses_changed_files(tmp_path: Path) -> None:
    from src.memory.vault_search import VaultIndex

    note_path = tmp_path / "note.md"
    _write_note(note_path, "# note\noriginal content")

    index = VaultIndex(tmp_path)
    index.refresh()

    time.sleep(0.01)
    _write_note(note_path, "# note\nupdated content")
    index.refresh()

    notes = index.notes()
    assert "updated content" in notes[0].content
