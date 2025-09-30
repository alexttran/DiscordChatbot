# rag/rag.py
from datetime import datetime

def answer(query: str, k: int = 4, provider: str = "azure"):
    """
    Temporary stub for the RAG pipeline.
    Later this will be replaced with:
      1. Document ingestion & embeddings
      2. Vector search for top-k chunks
      3. Azure DeepSeek R1 call
    """
    demo_answer = (
        f"(stub) I received your question: '{query}'.\n\n"
        "Example: Team Matching happens twice — Week 2 and Week 4. Attendance is mandatory. [1][2]"
    )
    return {
        "answer": demo_answer,
        "contexts": [
            {"source": "data/Intern FAQ - AI Bootcamp.pdf", "score": 0.88},
            {"source": "data/AI Bootcamp Journey & Learning Path.pdf", "score": 0.84}
        ],
        "meta": {
            "k": k,
            "provider": provider,
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
    }
