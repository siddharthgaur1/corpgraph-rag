"""Uniqueness constraints for every node type. Run once via `python -m graph.schema` or docker-compose init."""
from __future__ import annotations

from .neo4j_client import Neo4jClient

CONSTRAINTS = [
    "CREATE CONSTRAINT company_ticker IF NOT EXISTS FOR (c:Company) REQUIRE c.ticker IS UNIQUE",
    "CREATE CONSTRAINT director_din IF NOT EXISTS FOR (d:Director) REQUIRE d.din IS UNIQUE",
    "CREATE CONSTRAINT auditor_reg IF NOT EXISTS FOR (a:Auditor) REQUIRE a.registration_no IS UNIQUE",
    "CREATE CONSTRAINT promoter_name IF NOT EXISTS FOR (p:Promoter) REQUIRE p.name IS UNIQUE",
    "CREATE CONSTRAINT sebi_order_id IF NOT EXISTS FOR (o:SEBIOrder) REQUIRE o.order_id IS UNIQUE",
    "CREATE CONSTRAINT mf_name IF NOT EXISTS FOR (m:MutualFund) REQUIRE m.name IS UNIQUE",
]


def apply(client: Neo4jClient | None = None) -> None:
    client = client or Neo4jClient()
    for stmt in CONSTRAINTS:
        client.write(stmt)


if __name__ == "__main__":
    apply()
    print(f"Applied {len(CONSTRAINTS)} constraints.")
