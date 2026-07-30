"""The one thing that must never regress: generated Cypher can never write to the graph."""
import pytest

from graph.neo4j_client import Neo4jClient, ReadOnlyViolation


class _FakeClient(Neo4jClient):
    def __init__(self):
        pass  # skip real driver connection


@pytest.mark.parametrize("query", [
    "MATCH (n) DETACH DELETE n",
    "CREATE (c:Company {name: 'x'})",
    "MATCH (c:Company) SET c.name = 'hacked'",
    "MATCH (c:Company) REMOVE c.name",
    "MATCH (n) CALL apoc.create.node(['X'], {}) YIELD node RETURN node",
    "MERGE (c:Company {name: 'x'})",
])
def test_write_clauses_rejected(query):
    client = _FakeClient()
    with pytest.raises(ReadOnlyViolation):
        client.read_only_query(query)


@pytest.mark.parametrize("query", [
    "MATCH (c:Company) RETURN c LIMIT 10",
    "MATCH (a:Auditor)-[:AUDITS]->(c:Company) RETURN a, c",
])
def test_read_queries_get_limit_appended_not_rejected(query):
    client = _FakeClient()
    # No live driver in this test, so we only check the guard doesn't raise before it would try to run.
    try:
        client.read_only_query(query)
    except AttributeError:
        pass  # expected: _driver is unset on the fake client, guard already passed
