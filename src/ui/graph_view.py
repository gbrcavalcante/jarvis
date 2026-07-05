"""Graph View panel — renders the vault's note-link graph via QGraphicsView.

Pure PyQt6 (QGraphicsView/QGraphicsScene); no new dependency (research.md
Decision 5).
"""

from __future__ import annotations

import httpx
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QTextEdit,
    QWidget,
)

from src.memory.audit import get_logger

_log = get_logger("ui.graph_view")

_API_BASE = "http://127.0.0.1:37420"
_NODE_RADIUS = 8.0


class _NodeItem(QGraphicsEllipseItem):
    """A clickable graph node."""

    def __init__(self, node_id: str, x: float, y: float, on_click) -> None:  # type: ignore[no-untyped-def]
        super().__init__(x - _NODE_RADIUS, y - _NODE_RADIUS, _NODE_RADIUS * 2, _NODE_RADIUS * 2)
        self._node_id = node_id
        self._on_click = on_click
        self.setBrush(Qt.GlobalColor.blue)
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable, True)

    def mousePressEvent(self, event: object) -> None:  # type: ignore[override]
        self._on_click(self._node_id)


class GraphViewPanel(QWidget):
    """Renders the vault's note-link graph and shows note content on click."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._view = QGraphicsView(self._scene)
        self._content_panel = QTextEdit()
        self._content_panel.setReadOnly(True)

        layout = QHBoxLayout(self)
        layout.addWidget(self._view, stretch=2)
        layout.addWidget(self._content_panel, stretch=1)

    def node_count(self) -> int:
        return sum(1 for item in self._scene.items() if isinstance(item, _NodeItem))

    def edge_count(self) -> int:
        return sum(1 for item in self._scene.items() if isinstance(item, QGraphicsLineItem))

    def content_panel_text(self) -> str:
        return self._content_panel.toPlainText()

    def load_graph(self) -> None:
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{_API_BASE}/vault/graph")
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            _log.warning("graph_load_failed", error=str(exc))
            return
        self._render(data)

    def _render(self, data: dict) -> None:
        self._scene.clear()

        positions: dict[str, tuple[float, float]] = {}
        nodes = data.get("nodes", [])
        n = max(len(nodes), 1)
        for i, node in enumerate(nodes):
            import math
            angle = 2 * math.pi * i / n
            x, y = 200 * math.cos(angle), 200 * math.sin(angle)
            positions[node["id"]] = (x, y)

        for edge in data.get("edges", []):
            src = positions.get(edge["source"])
            dst = positions.get(edge["target"])
            if src is None or dst is None:
                continue
            line = QGraphicsLineItem(src[0], src[1], dst[0], dst[1])
            line.setPen(QPen(Qt.GlobalColor.gray))
            self._scene.addItem(line)

        for node in nodes:
            x, y = positions[node["id"]]
            item = _NodeItem(node["id"], x, y, self.on_node_clicked)
            self._scene.addItem(item)

    def on_node_clicked(self, node_id: str) -> None:
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{_API_BASE}/vault/notes/{node_id}")
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            _log.warning("note_load_failed", error=str(exc), note_id=node_id)
            return
        self._content_panel.setPlainText(data.get("content", ""))
