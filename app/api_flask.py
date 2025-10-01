
# app/api_flask.py
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from rag.rag import answer as rag_answer
from rag.rag import _get_retriever

app = Flask(__name__)
CORS(app, resources={r"/rag/*": {"origins": "*"}})

@app.errorhandler(Exception)
def handle_exc(e):
    if isinstance(e, HTTPException):
        return jsonify({"error": e.description}), e.code
    # print stack for local debugging
    import traceback; print(traceback.format_exc())
    return jsonify({"error": str(e), "kind": type(e).__name__}), 500

@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.post("/rag/answer")
def rag_api():
    data = request.get_json(force=True, silent=False) or {}
    query = data.get("query", "")
    k = int(data.get("k", 4))
    provider = data.get("provider", "azure")
    if not query:
        return jsonify({"error": "Missing 'query'"}), 400
    return jsonify(rag_answer(query, k=k, provider=provider))

@app.post("/rag/search")
def rag_search():
    data = request.get_json(force=True, silent=False) or {}
    query = data.get("query", "")
    k = int(data.get("k", 4))
    include_text = bool(data.get("include_text", False))
    if not query:
        return jsonify({"error": "Missing 'query'"}), 400
    ctxs = _get_retriever().search(query, k=k)
    if include_text:
        return jsonify(ctxs)
    # hide chunk text in default response
    return jsonify([{k:v for k,v in c.items() if k != "text"} for c in ctxs])

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)