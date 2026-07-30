"""Populate the graph end to end: schema, then yfinance company metadata.

BSE director scraping, MF holdings, and SEBI orders each need a data source
you supply (a bse_code map, portfolio URLs, or your SEBI Explorer export),
so they're not wired into this default run — call them directly once you
have that input, see their `if __name__` usage strings.
"""
from __future__ import annotations

import datetime

from graph import schema
from ingest import yfinance_companies


def main():
    print("Applying schema constraints...")
    schema.apply()
    print("Loading NIFTY500 seed company metadata from yfinance...")
    yfinance_companies.run(as_of_date=datetime.date.today().isoformat())
    print("Done. Run ingest.sebi_orders / bse_directors / mf_holdings separately once you have source data.")


if __name__ == "__main__":
    main()
