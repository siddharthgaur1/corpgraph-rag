# Changelog

## [Unreleased]

Baseline snapshot as of the portfolio hygiene pass (2026-08-04):

- GraphRAG pipeline: QueryUnderstander -> CypherGenerator -> Neo4jClient (read-only enforced) -> Enricher -> AnswerGenerator, with Streamlit/FastAPI frontends and a Pyvis subgraph view.
- Optional GATv2 link-prediction layer (`gnn/link_predictor.py`).
- `tests/test_read_only_guard.py` and `tests/test_cypher_generator.py` cover the write-safety guarantee independent of a running Neo4j instance.
- No measured accuracy for generated-Cypher correctness yet — tracked as an open issue.
