"""Scrape BSE corporate governance filings for director/auditor rosters.

BSE's page markup changes without notice, so the HTML parsing in `parse_governance_page`
is the one function you should expect to re-verify against a live page before a real run.
Everything else (the MERGE loading) is stable regardless of markup drift.
"""
from __future__ import annotations

import sys
import time

import requests
from bs4 import BeautifulSoup

from graph.neo4j_client import Neo4jClient

_GOVERNANCE_URL = "https://www.bseindia.com/corporates/Comp_Resign_dir.aspx?scripcd={bse_code}"
_HEADERS = {"User-Agent": "Mozilla/5.0 (research; corpgraph-rag)"}

_MERGE_DIRECTOR_SERVES = """
MERGE (d:Director {din: $din})
ON CREATE SET d.name = $director_name
SET d.designation = $designation
MERGE (c:Company {ticker: $ticker})
MERGE (d)-[s:SERVES_ON]->(c)
SET s.from_date = $from_date, s.to_date = $to_date, s.designation = $designation
"""

_MERGE_AUDITOR_AUDITS = """
MERGE (a:Auditor {registration_no: $registration_no})
ON CREATE SET a.firm_name = $firm_name
MERGE (c:Company {ticker: $ticker})
MERGE (a)-[r:AUDITS]->(c)
SET r.year = $year
"""


def fetch_governance_page(bse_code: str) -> str:
    resp = requests.get(_GOVERNANCE_URL.format(bse_code=bse_code), headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_governance_page(html: str) -> dict:
    """Returns {directors: [{din, name, designation, from_date, to_date}], auditors: [{registration_no, firm_name, year}]}.

    ponytail: selectors below target BSE's current table-based layout; if BSE reworks the
    page, only this function needs updating — ingest_company() and the MERGE queries don't change.
    """
    soup = BeautifulSoup(html, "html.parser")
    directors, auditors = [], []
    for row in soup.select("table.directors-table tr")[1:]:
        cells = [c.get_text(strip=True) for c in row.select("td")]
        if len(cells) >= 4:
            directors.append({
                "din": cells[0], "name": cells[1], "designation": cells[2],
                "from_date": cells[3], "to_date": cells[4] if len(cells) > 4 else None,
            })
    for row in soup.select("table.auditors-table tr")[1:]:
        cells = [c.get_text(strip=True) for c in row.select("td")]
        if len(cells) >= 3:
            auditors.append({"registration_no": cells[0], "firm_name": cells[1], "year": cells[2]})
    return {"directors": directors, "auditors": auditors}


def ingest_company(client: Neo4jClient, ticker: str, bse_code: str, rate_limit_s: float = 1.0) -> None:
    data = parse_governance_page(fetch_governance_page(bse_code))
    for d in data["directors"]:
        client.write(
            _MERGE_DIRECTOR_SERVES,
            din=d["din"], director_name=d["name"], designation=d["designation"],
            ticker=ticker, from_date=d["from_date"], to_date=d["to_date"],
        )
    for a in data["auditors"]:
        client.write(
            _MERGE_AUDITOR_AUDITS,
            registration_no=a["registration_no"], firm_name=a["firm_name"],
            ticker=ticker, year=a["year"],
        )
    time.sleep(rate_limit_s)  # ponytail: fixed courtesy delay; swap for a token-bucket limiter if run at scale


def run(company_bse_codes: dict[str, str]) -> None:
    """company_bse_codes: {ticker: bse_code}, e.g. {"RELIANCE.NS": "500325"}."""
    client = Neo4jClient()
    for i, (ticker, bse_code) in enumerate(company_bse_codes.items(), 1):
        try:
            ingest_company(client, ticker, bse_code)
            print(f"[{i}/{len(company_bse_codes)}] loaded {ticker}")
        except Exception as e:
            print(f"[{i}/{len(company_bse_codes)}] FAILED {ticker}: {e}", file=sys.stderr)
    client.close()


if __name__ == "__main__":
    print("Populate a {ticker: bse_code} mapping and call ingest.bse_directors.run(...) — no default list shipped.")
