"""NIFTY500 company metadata + promoter holdings, via yfinance. Idempotent (MERGE)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import yfinance as yf

from graph.neo4j_client import Neo4jClient

NIFTY500_CSV = Path(__file__).parent / "nifty500_tickers.csv"

_MERGE_COMPANY = """
MERGE (c:Company {ticker: $ticker})
SET c.name = $name, c.sector = $sector, c.market_cap = $market_cap,
    c.listing_date = $listing_date, c.bse_code = $bse_code
"""

_MERGE_PROMOTER_HOLDING = """
MERGE (p:Promoter {name: $promoter_name})
ON CREATE SET p.type = $promoter_type
MERGE (c:Company {ticker: $ticker})
MERGE (p)-[h:HOLDS]->(c)
SET h.stake_pct = $stake_pct, h.as_of_date = date($as_of_date)
"""


def load_tickers() -> list[str]:
    if not NIFTY500_CSV.exists():
        raise FileNotFoundError(
            f"{NIFTY500_CSV} not found. Populate it with one NSE ticker per line (e.g. RELIANCE.NS)."
        )
    with open(NIFTY500_CSV) as f:
        return [row[0].strip() for row in csv.reader(f) if row and row[0].strip()]


def ingest_company(client: Neo4jClient, ticker: str, as_of_date: str) -> None:
    info = yf.Ticker(ticker).info
    client.write(
        _MERGE_COMPANY,
        ticker=ticker,
        name=info.get("longName") or info.get("shortName") or ticker,
        sector=info.get("sector"),
        market_cap=info.get("marketCap"),
        listing_date=None,  # ponytail: yfinance doesn't expose listing date; backfill from BSE if needed
        bse_code=info.get("symbol"),
    )
    promoter_pct = info.get("heldPercentInsiders")
    if promoter_pct:
        client.write(
            _MERGE_PROMOTER_HOLDING,
            promoter_name=f"{ticker} Promoter Group",  # ponytail: yfinance doesn't name individual promoters
            promoter_type="institution",
            ticker=ticker,
            stake_pct=round(promoter_pct * 100, 2),
            as_of_date=as_of_date,
        )


def run(as_of_date: str) -> None:
    client = Neo4jClient()
    tickers = load_tickers()
    for i, ticker in enumerate(tickers, 1):
        try:
            ingest_company(client, ticker, as_of_date)
            print(f"[{i}/{len(tickers)}] loaded {ticker}")
        except Exception as e:  # noqa: BLE001 -- one bad row must not abort the batch
            print(f"[{i}/{len(tickers)}] FAILED {ticker}: {e}", file=sys.stderr)
    client.close()


if __name__ == "__main__":
    import datetime

    run(as_of_date=datetime.datetime.now(tz=datetime.timezone.utc).date().isoformat())
