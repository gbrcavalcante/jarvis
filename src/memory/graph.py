"""Derives a node/edge graph from vault note wiki-links for the Graph View.

Not persisted — computed on demand from the current VaultIndex.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

_ITERATIONS = 50
_AREA = 1000.0


@dataclass
class GraphNode:
    """A visual representation of a VaultNote in the graph view."""

    id: str
    label: str
    connection_count: int = 0
    x: float = 0.0
    y: float = 0.0


@dataclass
class GraphEdge:
    """A link between two GraphNodes, derived from a resolved wiki-link."""

    source: str
    target: str


@dataclass
class Graph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)


def build_graph_from_index(index: object) -> Graph:
    """Derive a Graph from a VaultIndex: nodes = notes, edges = resolved wiki-links."""
    notes = index.notes()  # type: ignore[attr-defined]
    by_stem = {note.path.stem.lower(): note for note in notes}

    node_ids = {note.path.stem.lower(): note.path.stem for note in notes}
    connection_counts = {stem: 0 for stem in node_ids}
    edges: list[GraphEdge] = []

    for note in notes:
        source_id = note.path.stem
        for link in note.links:
            target = by_stem.get(link.lower())
            if target is None:
                continue
            target_id = target.path.stem
            edges.append(GraphEdge(source=source_id, target=target_id))
            connection_counts[source_id.lower()] += 1
            connection_counts[target_id.lower()] += 1

    nodes = [
        GraphNode(
            id=note.path.stem,
            label=note.title,
            connection_count=connection_counts[note.path.stem.lower()],
        )
        for note in notes
    ]

    _layout(nodes, edges)
    return Graph(nodes=nodes, edges=edges)


def _layout(nodes: list[GraphNode], edges: list[GraphEdge]) -> None:
    """Fixed-iteration force-directed layout (Fruchterman-Reingold style)."""
    n = len(nodes)
    if n == 0:
        return

    # Deterministic circular initial placement
    for i, node in enumerate(nodes):
        angle = 2 * math.pi * i / n
        node.x = _AREA / 2 * math.cos(angle)
        node.y = _AREA / 2 * math.sin(angle)

    if n < 2:
        return

    k = math.sqrt(_AREA * _AREA / n)
    by_id = {node.id: node for node in nodes}

    for _ in range(_ITERATIONS):
        disp = {node.id: [0.0, 0.0] for node in nodes}

        for a in nodes:
            for b in nodes:
                if a.id == b.id:
                    continue
                dx, dy = a.x - b.x, a.y - b.y
                dist = math.hypot(dx, dy) or 0.01
                force = (k * k) / dist
                disp[a.id][0] += (dx / dist) * force
                disp[a.id][1] += (dy / dist) * force

        for edge in edges:
            a, b = by_id.get(edge.source), by_id.get(edge.target)
            if a is None or b is None:
                continue
            dx, dy = a.x - b.x, a.y - b.y
            dist = math.hypot(dx, dy) or 0.01
            force = (dist * dist) / k
            disp[a.id][0] -= (dx / dist) * force
            disp[a.id][1] -= (dy / dist) * force
            disp[b.id][0] += (dx / dist) * force
            disp[b.id][1] += (dy / dist) * force

        for node in nodes:
            dx, dy = disp[node.id]
            dist = math.hypot(dx, dy) or 0.01
            node.x += (dx / dist) * min(dist, 10.0)
            node.y += (dy / dist) * min(dist, 10.0)
