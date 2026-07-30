"""Parse SEBI order records (from your existing SEBI Explorer scrape output) into the graph.

Expects a JSONL file, one order per line, with fields:
    order_id, date, penalty_amount, violation_type, summary,
    companies: [str, ...], directors: [str, ...]
Adjust `parse_line` if your SEBI Explorer export uses different field names.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from graph.neo4j_client import Neo4jClient

_MERGE_ORDER = """
MERGE (o:SEBIOrder {order_id: $order_id})
SET o.date = date($date), o.penalty_amount = $penalty_amount,
    o.violation_type = $violation_type, o.summary = $summary
"""

_MERGE_COMPANY_PENALIZED = """
MERGE (c:Company {ticker: $ticker})
ON CREATE SET c.name = $company_name
MERGE (o:SEBIOrder {order_id: $order_id})
MERGE (c)-[:PENALIZED_BY]->(o)
"""

_MERGE_DIRECTOR_NAMED = """
MERGE (d:Director {name: $director_name})
MERGE (o:SEBIOrder {order_id: $order_id})
MERGE (d)-[:NAMED_IN]->(o)
"""


def parse_line(line: str) -> dict:
    return json.loads(line)


def ingest_order(client: Neo4jClient, order: dict) -> None:
    client.write(
        _MERGE_ORDER,
        order_id=order["order_id"],
        date=order["date"],
        penalty_amount=order.get("penalty_amount"),
        violation_type=order.get("violation_type"),
        summary=order.get("summary", ""),
    )
    for company in order.get("companies", []):
        # ponytail: no ticker resolution here; company name doubles as a stable key until
        # yfinance_companies.py MERGE-matches it onto the same node by ticker later.
        client.write(
            _MERGE_COMPANY_PENALIZED,
            ticker=company,
            company_name=company,
            order_id=order["order_id"],
        )
    for director in order.get("directors", []):
        client.write(_MERGE_DIRECTOR_NAMED, director_name=director, order_id=order["order_id"])


def run(jsonl_path: str) -> None:
    client = Neo4jClient()
    path = Path(jsonl_path)
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            ingest_order(client, parse_line(line))
            if i % 500 == 0:
                print(f"[{i}/{len(lines)}] orders loaded")
        except Exception as e:
            print(f"[{i}/{len(lines)}] FAILED: {e}", file=sys.stderr)
    client.close()
    print(f"Done: {len(lines)} order records processed from {path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m ingest.sebi_orders <path/to/sebi_orders.jsonl>")
        sys.exit(1)
    run(sys.argv[1])
