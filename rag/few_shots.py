"""15 (question -> Cypher) pairs, given to the Cypher-generation LLM call as few-shot context.

Every example is a MATCH/RETURN-only traversal against the schema in graph/schema.py —
no CREATE/MERGE/DELETE, matching the read-only contract enforced in Neo4jClient.read_only_query.
"""

FEW_SHOTS = [
    {
        "question": "Which auditors appear across multiple SEBI-penalized companies?",
        "cypher": """
MATCH (a:Auditor)-[:AUDITS]->(c:Company)-[:PENALIZED_BY]->(o:SEBIOrder)
WITH a, count(DISTINCT c) AS penalized_clients, collect(DISTINCT c.name) AS companies
WHERE penalized_clients > 1
RETURN a.firm_name AS auditor, penalized_clients, companies
ORDER BY penalized_clients DESC
LIMIT 25
""".strip(),
    },
    {
        "question": "Show me the director network connecting Adani and Ambani group companies.",
        "cypher": """
MATCH path = (c1:Company)<-[:SERVES_ON]-(d:Director)-[:SERVES_ON]->(c2:Company)
WHERE c1.name CONTAINS 'Adani' AND c2.name CONTAINS 'Reliance'
RETURN path
LIMIT 50
""".strip(),
    },
    {
        "question": "Which companies has director X served on the board of?",
        "cypher": """
MATCH (d:Director {name: $director_name})-[s:SERVES_ON]->(c:Company)
RETURN c.name AS company, c.ticker AS ticker, s.designation AS designation, s.from_date AS from_date, s.to_date AS to_date
ORDER BY s.from_date DESC
LIMIT 50
""".strip(),
    },
    {
        "question": "Find common directors between company A and company B.",
        "cypher": """
MATCH (d:Director)-[:SERVES_ON]->(c1:Company {ticker: $ticker_a})
MATCH (d)-[:SERVES_ON]->(c2:Company {ticker: $ticker_b})
RETURN d.name AS director, d.din AS din
LIMIT 50
""".strip(),
    },
    {
        "question": "Which auditor has the most SEBI-penalized clients?",
        "cypher": """
MATCH (a:Auditor)-[:AUDITS]->(c:Company)-[:PENALIZED_BY]->(:SEBIOrder)
RETURN a.firm_name AS auditor, count(DISTINCT c) AS penalized_clients
ORDER BY penalized_clients DESC
LIMIT 10
""".strip(),
    },
    {
        "question": "Show all SEBI orders naming director X.",
        "cypher": """
MATCH (d:Director {name: $director_name})-[:NAMED_IN]->(o:SEBIOrder)
RETURN o.order_id AS order_id, o.date AS date, o.violation_type AS violation_type, o.penalty_amount AS penalty_amount, o.summary AS summary
ORDER BY o.date DESC
LIMIT 50
""".strip(),
    },
    {
        "question": "Which companies are peers of company X?",
        "cypher": """
MATCH (c:Company {ticker: $ticker})-[:PEER_OF]->(peer:Company)
RETURN peer.name AS peer, peer.ticker AS ticker, peer.sector AS sector, peer.market_cap AS market_cap
LIMIT 25
""".strip(),
    },
    {
        "question": "Which mutual funds hold the largest stake in company X?",
        "cypher": """
MATCH (m:MutualFund)-[i:INVESTED_IN]->(c:Company {ticker: $ticker})
RETURN m.name AS fund, m.amc AS amc, i.units AS units, i.value AS value
ORDER BY i.value DESC
LIMIT 25
""".strip(),
    },
    {
        "question": "Show repeat SEBI offenders (companies penalized more than once).",
        "cypher": """
MATCH (c:Company)-[:PENALIZED_BY]->(o:SEBIOrder)
WITH c, count(o) AS n_orders, collect(o.order_id) AS orders
WHERE n_orders > 1
RETURN c.name AS company, c.ticker AS ticker, n_orders, orders
ORDER BY n_orders DESC
LIMIT 25
""".strip(),
    },
    {
        "question": "Which promoters hold stakes in more than one listed company?",
        "cypher": """
MATCH (p:Promoter)-[h:HOLDS]->(c:Company)
WITH p, count(DISTINCT c) AS n_companies, collect(c.name) AS companies
WHERE n_companies > 1
RETURN p.name AS promoter, n_companies, companies
ORDER BY n_companies DESC
LIMIT 25
""".strip(),
    },
    {
        "question": "What is the full profile of company X (directors, auditor, promoters, SEBI orders)?",
        "cypher": """
MATCH (c:Company {ticker: $ticker})
OPTIONAL MATCH (c)<-[:SERVES_ON]-(d:Director)
OPTIONAL MATCH (c)<-[:AUDITS]-(a:Auditor)
OPTIONAL MATCH (c)<-[:HOLDS]-(p:Promoter)
OPTIONAL MATCH (c)-[:PENALIZED_BY]->(o:SEBIOrder)
RETURN c AS company, collect(DISTINCT d.name) AS directors, collect(DISTINCT a.firm_name) AS auditors,
       collect(DISTINCT p.name) AS promoters, collect(DISTINCT o.order_id) AS sebi_orders
LIMIT 1
""".strip(),
    },
    {
        "question": "Which directors are named in the most SEBI orders?",
        "cypher": """
MATCH (d:Director)-[:NAMED_IN]->(o:SEBIOrder)
RETURN d.name AS director, count(o) AS n_orders
ORDER BY n_orders DESC
LIMIT 15
""".strip(),
    },
    {
        "question": "Show the 2-hop network around company X (directors, auditors, peers).",
        "cypher": """
MATCH (c:Company {ticker: $ticker})-[r]-(n)
RETURN c, r, n
LIMIT 100
""".strip(),
    },
    {
        "question": "Which companies in sector Y were penalized by SEBI for a specific violation type?",
        "cypher": """
MATCH (c:Company {sector: $sector})-[:PENALIZED_BY]->(o:SEBIOrder {violation_type: $violation_type})
RETURN c.name AS company, c.ticker AS ticker, o.order_id AS order_id, o.date AS date, o.penalty_amount AS penalty_amount
ORDER BY o.date DESC
LIMIT 25
""".strip(),
    },
    {
        "question": "Which director moved from one penalized company to another?",
        "cypher": """
MATCH (d:Director)-[:SERVES_ON]->(c1:Company)-[:PENALIZED_BY]->(:SEBIOrder)
MATCH (d)-[:SERVES_ON]->(c2:Company)-[:PENALIZED_BY]->(:SEBIOrder)
WHERE c1 <> c2
RETURN d.name AS director, c1.name AS company_1, c2.name AS company_2
LIMIT 25
""".strip(),
    },
]
