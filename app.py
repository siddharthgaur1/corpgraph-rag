"""Streamlit GraphRAG explorer: ask an investigative question, see the generated Cypher,
the traversed subgraph, and an LLM answer grounded in it.
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from graph.neo4j_client import Neo4jClient
from rag.llm import ClaudeLLM
from rag.pipeline import run_query
from viz.graph_renderer import render

st.set_page_config(page_title="corpgraph-rag", layout="wide")
st.title("corpgraph-rag — Corporate Knowledge Graph Explorer")

PRESETS = [
    "Show SEBI repeat offenders",
    "Find common directors between two companies",
    "Which auditors have most penalized clients",
]


@st.cache_resource
def _client():
    return Neo4jClient()


@st.cache_resource
def _llm():
    return ClaudeLLM()


if "question" not in st.session_state:
    st.session_state.question = ""

cols = st.columns(len(PRESETS))
for col, preset in zip(cols, PRESETS):
    if col.button(preset):
        st.session_state.question = preset

question = st.text_input("Ask an investigative question", value=st.session_state.question)

if st.button("Run query", type="primary") and question:
    with st.spinner("Understanding question -> generating Cypher -> traversing graph -> answering..."):
        result = run_query(question, client=_client(), llm=_llm())

    if result.error:
        st.error(result.error)
    else:
        with st.expander("Generated Cypher", expanded=False):
            st.code(result.cypher, language="cypher")

        st.subheader("Answer")
        st.write(result.answer.answer)

        if result.answer.key_findings:
            st.subheader("Key findings")
            for f in result.answer.key_findings:
                st.markdown(f"- {f}")

        if result.answer.evidence:
            st.subheader("Graph evidence")
            for e in result.answer.evidence:
                st.markdown(f"- {e}")

        if result.graph_rows:
            st.subheader("Subgraph")
            path = render(result.graph_rows, out_path="_streamlit_graph.html")
            with open(path, encoding="utf-8") as f:
                components.html(f.read(), height=620, scrolling=True)

        if result.answer.follow_ups:
            st.subheader("Suggested follow-ups")
            for i, fu in enumerate(result.answer.follow_ups):
                if st.button(fu, key=f"followup_{i}"):
                    st.session_state.question = fu
                    st.rerun()
