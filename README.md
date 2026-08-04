# corpgraph-rag

GraphRAG over a Neo4j knowledge graph of Indian corporate entities (companies, directors,
auditors, promoters, SEBI orders, mutual funds). Ask an investigative question in plain
English, get back an LLM-generated answer grounded in an actual graph traversal — plus the
Cypher that produced it and an interactive visualization of the subgraph.

## Architecture

```
                         ┌─────────────────────┐
   "which auditors  ───► │  QueryUnderstander   │  (LLM: question -> {entities, traversal_type,
    appear across        └──────────┬───────────┘   focus_relationship, intent})
    multiple SEBI-                  │
    penalized                       ▼
    companies?"          ┌─────────────────────┐
                         │  CypherGenerator      │  (LLM + 15 few-shot examples -> Cypher;
                         └──────────┬───────────┘   MATCH/RETURN only, write clauses rejected)
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  Neo4jClient          │  (read_only_query: rejects CREATE/MERGE/
                         │  .read_only_query()   │   DELETE/SET/REMOVE/CALL, enforces LIMIT,
                         └──────────┬───────────┘   10s timeout, READ access mode)
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  Enricher             │  (ChromaDB: SEBI order text snippets
                         └──────────┬───────────┘   for companies in the result set)
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  AnswerGenerator      │  (LLM: answer + key findings + evidence
                         └──────────┬───────────┘   citations + follow-up questions)
                                    │
                         ┌──────────┴───────────┐
                         ▼                       ▼
                  Streamlit / FastAPI     Pyvis subgraph (graph.html)
```

## Graph schema

```
(Director)-[:SERVES_ON {from_date, to_date, designation}]->(Company)
(Auditor)-[:AUDITS {year}]->(Company)
(Promoter)-[:HOLDS {stake_pct, as_of_date}]->(Company)
(Company)-[:PENALIZED_BY]->(SEBIOrder)
(Director)-[:NAMED_IN]->(SEBIOrder)
(Company)-[:PEER_OF]->(Company)
(MutualFund)-[:INVESTED_IN {units, value}]->(Company)
```

## Safety: no write queries, ever

The LLM only ever sees `graph/schema.py`'s node/edge shapes and 15 few-shot Cypher examples
(`rag/few_shots.py`) — never write access. `CypherGenerator` fast-fails on an obvious write
clause, but the actual guarantee is `Neo4jClient.read_only_query()`
(`graph/neo4j_client.py`): it regex-rejects CREATE/MERGE/DELETE/SET/REMOVE/DROP/CALL,
appends a LIMIT if missing, runs with a 10s timeout, and opens the Neo4j session in
`READ` access mode. See `tests/test_read_only_guard.py`.

## Setup

```bash
cp .env.example .env   # set ANTHROPIC_API_KEY
docker-compose up -d neo4j
pip install -r requirements.txt
python -m graph.schema                 # apply uniqueness constraints
python -m ingest.run_all               # schema + yfinance seed companies (20-ticker sample list)
```

`ingest/sebi_orders.py`, `ingest/bse_directors.py`, and `ingest/mf_holdings.py` each need a
data source you supply (your SEBI Explorer JSONL export, a `{ticker: bse_code}` map, or AMFI
portfolio URLs respectively) — call them directly once you have that input; see the
docstring in each file.

## Run

```bash
streamlit run app.py           # interactive explorer with preset queries
uvicorn api:app --reload       # POST /query, GET /entity/{name}, GET /graph/stats
```

Optional GNN layer (`pip install -r requirements-gnn.txt`):
```bash
python -m gnn.link_predictor    # trains GATv2, prints top-10 suspicious missing links
```

## Example queries

- "Which auditors appear across multiple SEBI-penalized companies?"
- "Show me the director network connecting Adani and Ambani group companies."
- "Show SEBI repeat offenders."
- "Find common directors between two companies."

## Tests

```bash
pytest
```

`tests/test_read_only_guard.py` is the one that matters most — it's the regression test for
"the LLM can never write to the graph," independent of whether Neo4j is running.

## Results

No accuracy number for generated-Cypher correctness or answer quality ships
in this repo — that needs a labeled set of questions with expected Cypher
or expected answers, which doesn't exist yet (`TODO(metric)`). What's
verified without any LLM call: `pytest tests/test_read_only_guard.py` — the
regression test for "the LLM can never write to the graph," independent of
whether Neo4j is even running.

## Limitations

No measured Cypher-generation accuracy (see Results above) — correctness
currently rests on the 15 few-shot examples and manual testing via the demo
queries, not a scored eval set.

## Notes on scope

- `ingest/nifty500_tickers.csv` ships a 20-ticker sample, not the full NIFTY500 — extend it for a bigger seed graph.
- `ingest/bse_directors.py`'s HTML selectors target BSE's current corporate-governance page layout; verify against a live page before a real scrape run (flagged inline).
- `rag/enricher.py` expects a ChromaDB collection built by a separate SEBI-order-embedding project; it degrades to no document enrichment if that collection isn't present.
