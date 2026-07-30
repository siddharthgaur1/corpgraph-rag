"""Step 5: generate the final structured answer from question + graph results + doc snippets."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

_PROMPT = """You are a financial investigation analyst. Answer the user's question using ONLY the
graph evidence and document snippets given below — do not invent facts not present in them.

Question: {question}

Graph traversal results:
{graph_text}

Document snippets:
{doc_text}

Output ONLY a JSON object (no markdown fences) with fields:
- answer: a direct answer paragraph
- key_findings: list of short bullet strings
- evidence: list of short strings, each citing which graph node/edge or document snippet supports a claim
- follow_ups: list of 2-4 suggested follow-up questions
"""


@dataclass
class Answer:
    answer: str = ""
    key_findings: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)


def generate(question: str, graph_text: str, doc_snippets: list[dict], llm) -> Answer:
    doc_text = "\n".join(f"- [{d.get('company')}] {d.get('snippet')}" for d in doc_snippets) or "None."
    prompt = _PROMPT.format(question=question, graph_text=graph_text, doc_text=doc_text)
    response = llm.complete(prompt)
    match = re.search(r"\{.*\}", response, re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        data = {"answer": response.strip()}  # ponytail: fall back to raw text rather than losing the answer
    return Answer(
        answer=data.get("answer", ""),
        key_findings=data.get("key_findings", []),
        evidence=data.get("evidence", []),
        follow_ups=data.get("follow_ups", []),
    )
