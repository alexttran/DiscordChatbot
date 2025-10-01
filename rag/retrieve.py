# rag/retrieve.py
import json, os
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors

STORE_DIR = Path("store")
EMB_MODEL = "intfloat/e5-base-v2"

class Retriever:
    def __init__(self):
        self.model = SentenceTransformer(EMB_MODEL)
        self.chunks = [json.loads(l) for l in open(STORE_DIR/"chunks.jsonl", encoding="utf-8")]
        self.embs = np.load(STORE_DIR/"embeddings.npy")
        self.nn = NearestNeighbors(n_neighbors=10, metric="cosine")
        self.nn.fit(self.embs)

    def search(self, query: str, k: int = 5):
        q = self.model.encode([query])
        dist, idx = self.nn.kneighbors(q, n_neighbors=k)
        out = []
        for d, i in zip(dist[0], idx[0]):
            c = self.chunks[int(i)]
            score = float(1.0 - d)  # cosine similarity
            title = os.path.basename(c.get("source",""))
            out.append({
                "text": c["text"],
                "source": c.get("source"),
                "title": title,
                "score": score
            })
        return out
