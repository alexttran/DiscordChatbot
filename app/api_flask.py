# app/api_flask.py
from flask import Flask, jsonify, request
from flask_cors import CORS
from rag.rag import answer as rag_answer

app = Flask(__name__)

CORS(app, resources={
    r"/health": {"origins": "*"},
    r"/rag/*": {"origins": "*"}
})

@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.post("/rag/answer")
def rag_api():
    try:
        data = request.get_json(force=True, silent=False) or {}
        query = data.get("query", "")
        k = int(data.get("k", 4))
        provider = data.get("provider", "azure")
        if not query:
            return jsonify({"error": "Missing 'query'"}), 400
        return jsonify(rag_answer(query, k=k, provider=provider))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # dev server
    app.run(host="127.0.0.1", port=8000, debug=True)
