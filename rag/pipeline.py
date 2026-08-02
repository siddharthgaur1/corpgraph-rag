"""Orchestrates all 5 GraphRAG steps for a single user question."""
from __future__ import annotations

from dataclasses import dataclass

from graph.neo4j_client import Neo4jClient, ReadOnlyViolation

from . import (
    answer_generator,
    cypher_generator,
    enricher,
    query_understander,
    traverser,
)
from .answer_generator import Answer
from .cypher_generator import UnsafeCypherError
from .llm import ClaudeLLM


@dataclass
class PipelineResult:
    cypher: str
    graph_rows: list[dict]
    answer: Answer
    error: str | None = None


def run_query(question: str, client: Neo4jClient | None = None, llm=None) -> PipelineResult:
    client = client or Neo4jClient()
    llm = llm or ClaudeLLM()

    plan = query_understander.understand(question, llm)

    try:
        cypher = cypher_generator.generate(plan, llm)
    except UnsafeCypherError as e:
        return PipelineResult(cypher="", graph_rows=[], answer=Answer(answer=""), error=str(e))

    try:
        rows = traverser.traverse(client, cypher)
    except ReadOnlyViolation as e:
        return PipelineResult(cypher=cypher, graph_rows=[], answer=Answer(answer=""), error=str(e))
    except Exception as e:  # noqa: BLE001 -- top-level pipeline guard, converts to error response instead of crashing
        return PipelineResult(cypher=cypher, graph_rows=[], answer=Answer(answer=""), error=f"Query execution failed: {e}")

    graph_text = traverser.serialize(rows)
    company_names = _extract_company_names(rows)
    doc_snippets = enricher.enrich(company_names)

    answer = answer_generator.generate(question, graph_text, doc_snippets, llm)
    return PipelineResult(cypher=cypher, graph_rows=rows, answer=answer)


def _extract_company_names(rows: list[dict]) -> list[str]:
    names = []
    for row in rows:
        for value in row.values():
            if isinstance(value, dict) and "name" in value:
                names.append(value["name"])
            elif isinstance(value, str) and len(value) < 100:
                names.append(value)
    return list(dict.fromkeys(names))  # de-dupe, preserve order
