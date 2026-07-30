"""AMFI monthly MF portfolio disclosures -> (MutualFund)-[:INVESTED_IN]->(Company) edges.

AMFI publishes each AMC's monthly portfolio disclosure as a downloadable Excel/CSV per
scheme; there's no single unified feed, so `fetch_portfolio_csv` takes a direct URL per
AMC/month. Column names below match the common AMFI template; verify against the AMC's
actual file before a real run (ponytail: this is a naming convention, not an API).
"""
from __future__ import annotations

import csv
import io
import sys

import requests

from graph.neo4j_client import Neo4jClient

_HEADERS = {"User-Agent": "Mozilla/5.0 (research; corpgraph-rag)"}

_MERGE_MF_INVESTMENT = """
MERGE (m:MutualFund {name: $fund_name})
ON CREATE SET m.amc = $amc, m.category = $category
MERGE (c:Company {ticker: $ticker})
ON CREATE SET c.name = $company_name
MERGE (m)-[i:INVESTED_IN]->(c)
SET i.units = $units, i.value = $value
"""


def fetch_portfolio_csv(url: str) -> str:
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_portfolio_csv(csv_text: str, fund_name: str, amc: str, category: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []
    for row in reader:
        ticker = (row.get("ISIN") or row.get("Ticker") or row.get("Instrument", "")).strip()
        if not ticker:
            continue
        rows.append({
            "fund_name": fund_name, "amc": amc, "category": category,
            "ticker": ticker, "company_name": row.get("Name of the Instrument", ticker),
            "units": _to_float(row.get("Quantity")), "value": _to_float(row.get("Market Value")),
        })
    return rows


def _to_float(value: str | None) -> float:
    try:
        return float(str(value).replace(",", "")) if value else 0.0
    except ValueError:
        return 0.0


def ingest_portfolio(client: Neo4jClient, url: str, fund_name: str, amc: str, category: str) -> None:
    rows = parse_portfolio_csv(fetch_portfolio_csv(url), fund_name, amc, category)
    for row in rows:
        client.write(_MERGE_MF_INVESTMENT, **row)


def run(portfolios: list[dict]) -> None:
    """portfolios: [{"url": ..., "fund_name": ..., "amc": ..., "category": ...}, ...]"""
    client = Neo4jClient()
    for i, p in enumerate(portfolios, 1):
        try:
            ingest_portfolio(client, **p)
            print(f"[{i}/{len(portfolios)}] loaded {p['fund_name']}")
        except Exception as e:
            print(f"[{i}/{len(portfolios)}] FAILED {p['fund_name']}: {e}", file=sys.stderr)
    client.close()


if __name__ == "__main__":
    print("Populate a list of {url, fund_name, amc, category} dicts and call ingest.mf_holdings.run(...).")
