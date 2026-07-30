"""Step 2: LLM + few-shot Cypher generation. Safety is enforced downstream by
Neo4jClient.read_only_query (the only place queries actually execute), not here —
this module's own check is a fast-fail for a clearly bad generation, not the guarantee.
"""
from __future__ import annotations

import re

from .few_shots import FEW_SHOTS
from .query_understander import QueryPlan

_SCHEMA_CONTEXT = """Schema:
Nodes: Company {name, ticker, sector, market_cap, listing_date, bse_code}
       Director {name, din, designation}
       Auditor {firm_name, registration_no}
       Promoter {name, type}
       SEBIOrder {order_id, date, penalty_amount, violation_type, summary}
       MutualFund {name, amc, category}
Relationships: (Director)-[:SERVES_ON {from_date, to_date, designation}]->(Company)
               (Auditor)-[:AUDITS {year}]->(Company)
               (Promoter)-[:HOLDS {stake_pct, as_of_date}]->(Company)
               (Company)-[:PENALIZED_BY]->(SEBIOrder)
               (Director)-[:NAMED_IN]->(SEBIOrder)
               (Company)-[:PEER_OF]->(Company)
               (MutualFund)-[:INVESTED_IN {units, value}]->(Company)
"""

_PROMPT_TEMPLATE = """You write read-only Cypher queries for a Neo4j graph of Indian corporate entities.
Rules: MATCH/OPTIONAL MATCH/WHERE/WITH/RETURN/ORDER BY/LIMIT only. Never CREATE, MERGE, DELETE, SET, REMOVE, or CALL.
Always include a LIMIT clause (100 max). Output ONLY the Cypher query, no prose, no markdown fences.

{schema}

Examples:
{examples}

Query plan: entities={entities}, traversal_type={traversal_type}, focus_relationship={focus_relationship}, intent={intent}
Question: {question}
Cypher:"""

_ALLOWED_CLAUSES = re.compile(
    r"^\s*(MATCH|OPTIONAL MATCH|WHERE|WITH|RETURN|ORDER BY|LIMIT|AND|OR|UNWIND)\b", re.IGNORECASE
)
_FORBIDDEN = re.compile(r"\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP|CALL)\b", re.IGNORECASE)


class UnsafeCypherError(Exception):
    pass


def generate(plan: QueryPlan, llm) -> str:
    examples = "\n\n".join(f"Q: {ex['question']}\nCypher:\n{ex['cypher']}" for ex in FEW_SHOTS)
    prompt = _PROMPT_TEMPLATE.format(
        schema=_SCHEMA_CONTEXT,
        examples=examples,
        entities=plan.entities,
        traversal_type=plan.traversal_type,
        focus_relationship=plan.focus_relationship,
        intent=plan.intent,
        question=plan.raw_question,
    )
    cypher = _strip_fences(llm.complete(prompt)).strip()
    if _FORBIDDEN.search(cypher):
        raise UnsafeCypherError(f"Generated query contains a write clause:\n{cypher}")
    return cypher


def _strip_fences(text: str) -> str:
    text = re.sub(r"^```(?:cypher)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    return text
