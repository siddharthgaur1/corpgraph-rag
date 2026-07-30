"""Thin wrapper around the Neo4j driver: connection handling + a read-only guard for RAG queries."""
from __future__ import annotations

import os
import re
from typing import Any

from neo4j import GraphDatabase

_WRITE_CLAUSES = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH DELETE|SET|REMOVE|DROP|CALL\s+db\.|CALL\s+apoc\.)\b", re.IGNORECASE
)


class ReadOnlyViolation(Exception):
    """Raised when a Cypher query generated for the RAG pipeline contains a write clause."""


class Neo4jClient:
    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None):
        self.uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.environ.get("NEO4J_USER", "neo4j")
        self.password = password or os.environ.get("NEO4J_PASSWORD", "corpgraph")
        self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        self._driver.close()

    def write(self, query: str, **params) -> list[dict[str, Any]]:
        """Unrestricted write access, for ingestion scripts only. Never call this from the RAG pipeline."""
        with self._driver.session() as session:
            return [dict(r) for r in session.run(query, **params)]

    def read_only_query(self, query: str, timeout_s: int = 10, limit: int = 100, **params) -> list[dict[str, Any]]:
        """The only entry point the RAG pipeline is allowed to use. Rejects anything but MATCH/RETURN traversal."""
        if _WRITE_CLAUSES.search(query):
            raise ReadOnlyViolation(f"Generated Cypher contains a write clause, refusing to execute:\n{query}")
        if not re.search(r"\bLIMIT\s+\d+", query, re.IGNORECASE):
            query = f"{query.rstrip().rstrip(';')}\nLIMIT {limit}"
        with self._driver.session(default_access_mode="READ") as session:
            result = session.run(query, timeout=timeout_s, **params)
            return [dict(r) for r in result]

    def stats(self) -> dict:
        with self._driver.session(default_access_mode="READ") as session:
            nodes = session.run(
                "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY n DESC"
            ).data()
            rels = session.run(
                "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS n ORDER BY n DESC"
            ).data()
        return {"nodes": nodes, "relationships": rels}
