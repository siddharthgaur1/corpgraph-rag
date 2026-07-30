from rag.cypher_generator import _FORBIDDEN
from rag.few_shots import FEW_SHOTS


def test_few_shot_examples_are_all_read_only():
    for ex in FEW_SHOTS:
        assert not _FORBIDDEN.search(ex["cypher"]), f"few-shot example contains a write clause: {ex['question']}"


def test_forbidden_pattern_catches_write_clauses():
    assert _FORBIDDEN.search("CREATE (n)")
    assert _FORBIDDEN.search("MATCH (n) SET n.x = 1")
    assert _FORBIDDEN.search("MATCH (n) DELETE n")
    assert not _FORBIDDEN.search("MATCH (n) RETURN n LIMIT 10")
