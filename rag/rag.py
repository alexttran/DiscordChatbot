# rag/rag.py
"""
RAG brain: retrieve → generate. Stable response shape.
"""
from datetime import datetime
from typing import Dict, Any
from rag.retrieve import Retriever
from rag.generate import generate_answer

_retriever = None

def _get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever

def answer(query: str, k: int = 4, provider: str = "azure") -> Dict[str, Any]:
    retriever = _get_retriever()
    contexts = retriever.search(query, k=k)

    # Guardrail: if evidence too weak, don't guess
    if not contexts or float(contexts[0].get("score", 0.0)) < 0.55:
        return {
            "answer": "I couldn’t find a reliable answer in the provided documents.",
            "contexts": [{k:v for k,v in c.items() if k != "text"} for c in contexts],
            "meta": {"k": k, "provider": provider, "generated_at": datetime.utcnow().isoformat()+"Z"}
        }

    text = generate_answer(query, contexts, provider=provider)
    return {
        "answer": text,
        "contexts": [{k:v for k,v in c.items() if k != "text"} for c in contexts],
        "meta": {"k": k, "provider": provider, "generated_at": datetime.utcnow().isoformat()+"Z"}
    }