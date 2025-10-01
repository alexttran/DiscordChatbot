# rag/ingest.py
import os, json, uuid
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
import tiktoken
from pypdf import PdfReader
from docx import Document

ENC = tiktoken.get_encoding("cl100k_base")
DATA_DIR = Path("data")
STORE_DIR = Path("store")
EMB_MODEL = "intfloat/e5-base-v2"

def read_txt(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def read_pdf(p: Path) -> str:
    reader = PdfReader(str(p))
    return "\n".join([(pg.extract_text() or "") for pg in reader.pages])

def read_docx(p: Path) -> str:
    doc = Document(str(p))
    return "\n".join([para.text for para in doc.paragraphs])

def load_docs():
    docs = []
    for p in DATA_DIR.glob("**/*"):
        if p.suffix.lower() in [".txt", ".pdf", ".docx", ".md"]:
            if p.name.startswith("Discord RAG FAQ Chatbot"):
                continue  # skip meta doc
            if p.suffix.lower()==".pdf":
                text = read_pdf(p)
            elif p.suffix.lower()==".docx":
                text = read_docx(p)
            else:
                text = read_txt(p)
            if text.strip():
                docs.append({"id": str(uuid.uuid4()), "path": str(p), "text": text})
    return docs

def chunk(text: str, max_tokens=400, overlap=60):
    toks = ENC.encode(text)
    i, chunks = 0, []
    while i < len(toks):
        piece = toks[i:i+max_tokens]
        chunks.append(ENC.decode(piece))
        i += max_tokens - overlap
    return chunks

def main():
    docs = load_docs()
    all_chunks = []
    for d in docs:
        for i, ch in enumerate(chunk(d["text"])):
            all_chunks.append({
                "doc_id": d["id"],
                "source": d["path"],
                "chunk_id": f"{d['id']}::{i}",
                "text": ch
            })
    if not all_chunks:
        raise SystemExit("No docs found in ./data. Put your 3 files there (.docx/.pdf).")

    STORE_DIR.mkdir(exist_ok=True)
    model = SentenceTransformer(EMB_MODEL)
    texts = [c["text"] for c in all_chunks]
    embs = model.encode(texts, normalize_embeddings=False, batch_size=32)
    np.save(STORE_DIR / "embeddings.npy", embs)

    with open(STORE_DIR / "chunks.jsonl", "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    with open(STORE_DIR / "meta.json", "w") as f:
        json.dump({"model": EMB_MODEL, "count": len(all_chunks)}, f)

    print(f"Saved {len(all_chunks)} chunks and embeddings → store/")

if __name__ == "__main__":
    main()
