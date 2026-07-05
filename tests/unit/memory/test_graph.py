"""Tests for graph derivation from vault note links (US4)."""

from __future__ import annotations

from pathlib import Path


def _write_note(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# T044 — one edge per resolved [[wiki-link]]; unresolved links dropped
# ---------------------------------------------------------------------------

def test_build_graph_creates_edge_for_resolved_link(tmp_path: Path) -> None:
    from src.memory.vault_search import VaultIndex
    from src.memory.graph import build_graph_from_index

    _write_note(tmp_path / "jarvis.md", "# jarvis\n\nSee [[voice-ui]].")
    _write_note(tmp_path / "voice-ui.md", "# voice-ui\n\nParent: [[jarvis]].")

    index = VaultIndex(tmp_path)
    index.refresh()
    graph = build_graph_from_index(index)

    assert len(graph.nodes) == 2
    assert len(graph.edges) == 2  # jarvis->voice-ui and voice-ui->jarvis


def test_build_graph_drops_unresolved_links(tmp_path: Path) -> None:
    from src.memory.vault_search import VaultIndex
    from src.memory.graph import build_graph_from_index

    _write_note(tmp_path / "jarvis.md", "# jarvis\n\nSee [[does-not-exist]].")

    index = VaultIndex(tmp_path)
    index.refresh()
    graph = build_graph_from_index(index)

    assert len(graph.nodes) == 1
    assert len(graph.edges) == 0


# ---------------------------------------------------------------------------
# T045 — GraphNode.connection_count equals edges touching that node
# ---------------------------------------------------------------------------

def test_graph_node_connection_count(tmp_path: Path) -> None:
    from src.memory.vault_search import VaultIndex
    from src.memory.graph import build_graph_from_index

    _write_note(tmp_path / "hub.md", "# hub\n\n[[a]] [[b]] [[c]]")
    _write_note(tmp_path / "a.md", "# a\ncontent")
    _write_note(tmp_path / "b.md", "# b\ncontent")
    _write_note(tmp_path / "c.md", "# c\ncontent")

    index = VaultIndex(tmp_path)
    index.refresh()
    graph = build_graph_from_index(index)

    hub_node = next(n for n in graph.nodes if n.label == "hub")
    assert hub_node.connection_count == 3


def test_graph_nodes_have_positions(tmp_path: Path) -> None:
    from src.memory.vault_search import VaultIndex
    from src.memory.graph import build_graph_from_index

    _write_note(tmp_path / "a.md", "# a\n\n[[b]]")
    _write_note(tmp_path / "b.md", "# b\ncontent")

    index = VaultIndex(tmp_path)
    index.refresh()
    graph = build_graph_from_index(index)

    for node in graph.nodes:
        assert isinstance(node.x, float)
        assert isinstance(node.y, float)
