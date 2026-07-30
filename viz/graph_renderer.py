"""Renders Neo4j query result rows (nodes + relationships) as an interactive Pyvis HTML graph."""
from __future__ import annotations

from neo4j.graph import Node, Relationship
from pyvis.network import Network

_COLORS = {
    "Company": "#1f77b4", "Director": "#2ca02c", "Auditor": "#ff7f0e",
    "SEBIOrder": "#d62728", "Promoter": "#9467bd", "MutualFund": "#8c564b",
}


def render(rows: list[dict], out_path: str = "graph.html") -> str:
    net = Network(height="600px", width="100%", directed=True, notebook=False, cdn_resources="in_line")
    seen_nodes = set()

    for row in rows:
        for value in row.values():
            if isinstance(value, Node):
                _add_node(net, value, seen_nodes)
            elif isinstance(value, Relationship):
                _add_node(net, value.start_node, seen_nodes)
                _add_node(net, value.end_node, seen_nodes)
                net.add_edge(value.start_node.element_id, value.end_node.element_id, label=value.type)

    net.write_html(out_path, notebook=False)
    return out_path


def _add_node(net: Network, node: Node, seen: set) -> None:
    if node.element_id in seen:
        return
    seen.add(node.element_id)
    label = next(iter(node.labels), "Node")
    title = "<br>".join(f"{k}: {v}" for k, v in dict(node).items())
    display_name = node.get("name") or node.get("firm_name") or node.get("order_id") or label
    net.add_node(node.element_id, label=str(display_name), title=title, color=_COLORS.get(label, "#999999"))
