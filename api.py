from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from graph.neo4j_client import Neo4jClient
from rag.llm import ClaudeLLM
from rag.pipeline import run_query
from viz.graph_renderer import render

app = FastAPI(title="corpgraph-rag")
_client = Neo4jClient()
_llm = ClaudeLLM()


class QueryRequest(BaseModel):
    question: str


@app.post("/query")
def query(req: QueryRequest):
    result = run_query(req.question, client=_client, llm=_llm)
    if result.error:
        raise HTTPException(status_code=400, detail=result.error)
    viz_path = render(result.graph_rows, out_path="static_graph.html")
    return {
        "cypher": result.cypher,
        "graph_data": result.graph_rows,
        "answer": result.answer.__dict__,
        "follow_ups": result.answer.follow_ups,
        "visualization_html": viz_path,
    }


@app.get("/entity/{name}")
def entity(name: str):
    rows = _client.read_only_query(
        "MATCH (n {name: $name})-[r]-(m) RETURN n, type(r) AS rel, m LIMIT 100", name=name
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"No entity named {name!r} found")
    return {"name": name, "relationships": rows}


@app.get("/graph/stats")
def graph_stats():
    return _client.stats()
