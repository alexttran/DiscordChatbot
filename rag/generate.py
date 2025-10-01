# rag/generate.py
import os, re
from textwrap import dedent
from typing import List, Dict
from openai import OpenAI  # pip install openai>=1.51.0

def _make_prompt(query: str, contexts: List[Dict]) -> str:
    ctx = "\n\n".join([f"[{i+1}] {c.get('text','')}" for i, c in enumerate(contexts)])
    return dedent(f"""
    You are a helpful assistant. Answer ONLY using the context. If the answer is not in the context, say you don't know.

    Question: {query}

    Context:
    {ctx}

    Requirements:
    - Be concise.
    - Cite sources like [1], [2] that correspond to the context indices above.
    """).strip()

def _strip_think(text: str) -> str:
    # Remove DeepSeek <think> blocks from output
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)

def _azure_foundry_call(prompt: str) -> str:
    # .env:
    # AZURE_OPENAI_ENDPOINT=https://aifoundary-rag.services.ai.azure.com/
    # AZURE_OPENAI_API_KEY=...
    # AZURE_OPENAI_API_VERSION=2024-05-01-preview  (not used by SDK call, kept for reference)
    # AZURE_OPENAI_MODEL=DeepSeek-R1               (DEPLOYMENT name)
    base = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    key  = os.environ["AZURE_OPENAI_API_KEY"]
    deployment = os.environ.get("AZURE_OPENAI_MODEL", "DeepSeek-R1")

    client = OpenAI(base_url=f"{base}/openai/v1", api_key=key)
    resp = client.chat.completions.create(
        model=deployment,  # deployment name from AI Foundry → Deployments
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return _strip_think(resp.choices[0].message.content.strip())

def generate_answer(query: str, contexts: List[Dict], provider: str = "azure") -> str:
    prompt = _make_prompt(query, contexts)
    return _azure_foundry_call(prompt)
