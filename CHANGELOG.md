# Changelog

## [Unreleased]

- 2026-08-27: Pinned `requirements.txt` to versions verified against the test suite.
- 2026-08-27: Added CI/Python/license/Neo4j badges and a real app screenshot to the README.
- 2026-08-22: Added a portfolio nav link and CI/license badges.
- 2026-08-06: Added a 1280x640 social preview card.

Baseline snapshot as of the portfolio hygiene pass (2026-08-04):

- GraphRAG pipeline: QueryUnderstander -> CypherGenerator -> Neo4jClient (read-only enforced) -> Enricher -> AnswerGenerator, with Streamlit/FastAPI frontends and a Pyvis subgraph view.
- Optional GATv2 link-prediction layer (`gnn/link_predictor.py`).
- `tests/test_read_only_guard.py` and `tests/test_cypher_generator.py` cover the write-safety guarantee independent of a running Neo4j instance.
- No measured accuracy for generated-Cypher correctness yet — tracked as an open issue.
