"""GATv2 link prediction on the corporate graph: predict likely undisclosed relationships
(e.g. hidden common directors) by scoring node pairs that aren't yet connected.

Optional layer — the RAG pipeline and Streamlit app work without it. Run as a script to
train and print the top-10 highest-scoring missing links.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GATv2Conv
from torch_geometric.utils import negative_sampling

from graph.neo4j_client import Neo4jClient

_FETCH_EDGES = """
MATCH (a)-[r]->(b)
WHERE any(l IN labels(a) WHERE l IN ['Company','Director','Auditor','Promoter'])
  AND any(l IN labels(b) WHERE l IN ['Company','Director','Auditor','Promoter'])
RETURN elementId(a) AS src, elementId(b) AS dst, labels(a)[0] AS src_label, labels(b)[0] AS dst_label
LIMIT 20000
"""


class LinkPredictorGATv2(torch.nn.Module):
    def __init__(self, num_nodes: int, embed_dim: int = 64, hidden_dim: int = 64, heads: int = 4):
        super().__init__()
        self.embedding = torch.nn.Embedding(num_nodes, embed_dim)
        self.conv1 = GATv2Conv(embed_dim, hidden_dim, heads=heads, dropout=0.2)
        self.conv2 = GATv2Conv(hidden_dim * heads, hidden_dim, heads=1, dropout=0.2)

    def encode(self, edge_index: torch.Tensor) -> torch.Tensor:
        x = self.embedding.weight
        x = F.elu(self.conv1(x, edge_index))
        return self.conv2(x, edge_index)

    def decode(self, z: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        return (z[edge_index[0]] * z[edge_index[1]]).sum(dim=-1)


def build_graph_data(client: Neo4jClient | None = None) -> tuple[Data, dict, dict]:
    client = client or Neo4jClient()
    rows = client.read_only_query(_FETCH_EDGES, limit=20000)
    node_ids = sorted({r["src"] for r in rows} | {r["dst"] for r in rows})
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    idx_to_label = {}
    for r in rows:
        idx_to_label[id_to_idx[r["src"]]] = r["src_label"]
        idx_to_label[id_to_idx[r["dst"]]] = r["dst_label"]
    edge_index = torch.tensor(
        [[id_to_idx[r["src"]] for r in rows], [id_to_idx[r["dst"]] for r in rows]], dtype=torch.long
    )
    data = Data(edge_index=edge_index, num_nodes=len(node_ids))
    return data, id_to_idx, idx_to_label


def train(data: Data, epochs: int = 100, lr: float = 0.01) -> LinkPredictorGATv2:
    model = LinkPredictorGATv2(num_nodes=data.num_nodes)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    n_edges = data.edge_index.size(1)
    perm = torch.randperm(n_edges)
    split = int(n_edges * 0.9)
    train_edges = data.edge_index[:, perm[:split]]
    val_edges = data.edge_index[:, perm[split:]]

    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        z = model.encode(train_edges)

        neg_edges = negative_sampling(train_edges, num_nodes=data.num_nodes, num_neg_samples=train_edges.size(1))
        pos_score = model.decode(z, train_edges)
        neg_score = model.decode(z, neg_edges)
        scores = torch.cat([pos_score, neg_score])
        labels = torch.cat([torch.ones_like(pos_score), torch.zeros_like(neg_score)])
        loss = F.binary_cross_entropy_with_logits(scores, labels)
        loss.backward()
        optimizer.step()

        if epoch % 20 == 0 or epoch == epochs - 1:
            auc = _eval_auc(model, train_edges, val_edges, data.num_nodes)
            print(f"epoch {epoch}: loss={loss.item():.4f} val_auc={auc:.4f}")

    return model


def _eval_auc(model: LinkPredictorGATv2, train_edges: torch.Tensor, val_edges: torch.Tensor, num_nodes: int) -> float:
    from sklearn.metrics import roc_auc_score

    model.eval()
    with torch.no_grad():
        z = model.encode(train_edges)
        neg_edges = negative_sampling(val_edges, num_nodes=num_nodes, num_neg_samples=val_edges.size(1))
        pos_score = torch.sigmoid(model.decode(z, val_edges))
        neg_score = torch.sigmoid(model.decode(z, neg_edges))
        y_true = torch.cat([torch.ones_like(pos_score), torch.zeros_like(neg_score)]).numpy()
        y_score = torch.cat([pos_score, neg_score]).numpy()
    return roc_auc_score(y_true, y_score)


def top_missing_links(model: LinkPredictorGATv2, data: Data, idx_to_label: dict, k: int = 10) -> list[tuple[int, int, float]]:
    """Score a random sample of non-edges and return the k highest-scoring pairs (candidate hidden links)."""
    model.eval()
    with torch.no_grad():
        z = model.encode(data.edge_index)
        existing = {(int(s), int(d)) for s, d in data.edge_index.t().tolist()}
        candidates = negative_sampling(data.edge_index, num_nodes=data.num_nodes, num_neg_samples=2000)
        scores = torch.sigmoid(model.decode(z, candidates))
        ranked = sorted(zip(candidates.t().tolist(), scores.tolist()), key=lambda x: -x[1])
    results = []
    for (src, dst), score in ranked:
        if (src, dst) not in existing:
            results.append((src, dst, score))
        if len(results) == k:
            break
    return results


if __name__ == "__main__":
    data, id_to_idx, idx_to_label = build_graph_data()
    idx_to_id = {v: k for k, v in id_to_idx.items()}
    model = train(data)
    print("\nTop-10 suspicious missing links:")
    for src, dst, score in top_missing_links(model, data, idx_to_label):
        print(f"  {idx_to_label.get(src)}({idx_to_id[src]}) <-> {idx_to_label.get(dst)}({idx_to_id[dst]}): {score:.3f}")
