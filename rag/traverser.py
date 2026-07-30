"""Step 3: execute the generated Cypher and serialize results into structured text for the LLM."""
from __future__ import annotations

from graph.neo4j_client import Neo4jClient


def traverse(client: Neo4jClient, cypher: str, **params) -> list[dict]:
    return client.read_only_query(cypher, **params)


def serialize(rows: list[dict]) -> str:
    """Turn raw Neo4j records into short natural-language lines an LLM can cite from."""
    if not rows:
        return "No matching results in the graph."
    lines = []
    for row in rows[:50]:
        parts = [f"{k}={_fmt(v)}" for k, v in row.items()]
        lines.append(", ".join(parts))
    return "\n".join(lines)


def _fmt(value) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(str(v) for v in value[:10]) + ("..." if len(value) > 10 else "") + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}: {v}" for k, v in value.items()) + "}"
    return str(value)
