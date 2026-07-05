"""Tests for the Graph View panel (US4, T049)."""

from __future__ import annotations

from unittest.mock import patch

_FAKE_GRAPH = {
    "nodes": [
        {"id": "jarvis", "label": "jarvis", "connection_count": 1},
        {"id": "voice-ui", "label": "voice-ui", "connection_count": 1},
    ],
    "edges": [{"source": "jarvis", "target": "voice-ui"}],
}


def test_graph_view_renders_node_and_edge_items(qtbot) -> None:
    """The panel renders one item per GraphNode and one line per GraphEdge."""
    from src.ui.graph_view import GraphViewPanel

    with patch("httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.return_value.json.return_value = _FAKE_GRAPH
        mock_client.get.return_value.raise_for_status.return_value = None

        panel = GraphViewPanel()
        qtbot.addWidget(panel)
        panel.load_graph()

    assert panel.node_count() == 2
    assert panel.edge_count() == 1


def test_graph_view_click_node_loads_content(qtbot) -> None:
    """Clicking a node fetches its content via GET /vault/notes/{id} and shows it."""
    from src.ui.graph_view import GraphViewPanel

    with patch("httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.return_value.json.return_value = _FAKE_GRAPH
        mock_client.get.return_value.raise_for_status.return_value = None

        panel = GraphViewPanel()
        qtbot.addWidget(panel)
        panel.load_graph()

        mock_client.get.return_value.json.return_value = {
            "id": "jarvis", "title": "jarvis", "content": "# jarvis\n\nHello",
        }
        panel.on_node_clicked("jarvis")

    assert "Hello" in panel.content_panel_text()
