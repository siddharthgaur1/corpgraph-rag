"""Step 1: turn a free-text investigative question into a structured query plan."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

_PROMPT = """You analyze investigative questions about Indian corporate entities (companies, \
directors, auditors, promoters, SEBI orders, mutual funds) for a graph database query planner.

Given the question, output ONLY a JSON object (no prose, no markdown fences) with these fields:
- entities: list of named entities mentioned (company names, tickers, director names, sectors, violation types)
- traversal_type: one of "2-hop", "path", "community", "lookup"
- focus_relationship: the single most relevant relationship type, one of
  SERVES_ON, AUDITS, HOLDS, PENALIZED_BY, NAMED_IN, PEER_OF, INVESTED_IN, or null
- intent: one of "investigative", "comparative", "network", "lookup"

Question: {question}
JSON:"""


@dataclass
class QueryPlan:
    entities: list[str] = field(default_factory=list)
    traversal_type: str = "lookup"
    focus_relationship: str | None = None
    intent: str = "lookup"
    raw_question: str = ""


def understand(question: str, llm) -> QueryPlan:
    """llm: any object with .complete(prompt) -> str-like response (see rag.pipeline for the default)."""
    response = llm.complete(_PROMPT.format(question=question))
    text = _strip_fences(response)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {}  # ponytail: judge/LLM output malformed, fall back to a lookup plan rather than crash
    return QueryPlan(
        entities=data.get("entities", []),
        traversal_type=data.get("traversal_type", "lookup"),
        focus_relationship=data.get("focus_relationship"),
        intent=data.get("intent", "lookup"),
        raw_question=question,
    )


def _strip_fences(text: str) -> str:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text
