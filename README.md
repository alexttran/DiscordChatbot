Discord RAG Backend — Working RAG + Azure Foundry Integration

This backend powers the Discord RAG Chatbot with advanced Retrieval-Augmented Generation (RAG).
It combines Flask, FAISS, and Azure AI Foundry (DeepSeek-R1) to deliver context-aware, explainable answers.

⚙️ Tech Stack

Flask — Lightweight REST API backend

FAISS — Vector search engine for retrieval

Azure AI Foundry (DeepSeek-R1) — LLM-based generation

Logging & Observability — JSON logs + in-memory metrics

Docker — Containerized deployment

🧩 Project Structure
DiscordChatbot/
│
├── app/
│   └── api_flask.py       # Main Flask backend
│
├── rag/
│   ├── rag.py             # RAG brain (retrieve → generate)
│   ├── retrieve.py        # FAISS retriever
│   └── generate.py        # Azure Foundry text generation
│
├── logs/                  # Log files
├── requirements.txt
├── Dockerfile
├── .dockerignore
└── .env

🧠 Environment Setup
1️⃣ Clone the repo
git clone https://github.com/alexttran/DiscordChatbot.git
cd DiscordChatbot

2️⃣ Create a virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# or
source venv/bin/activate   # Mac/Linux

3️⃣ Install dependencies
pip install -r requirements.txt

4️⃣ Create .env file

Create it in your project root (next to requirements.txt):

AZURE_OPENAI_ENDPOINT=https://aifoundary-rag.services.ai.azure.com
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_API_VERSION=2024-05-01-preview
AZURE_OPENAI_MODEL=DeepSeek-R1

🧪 Run Locally
python -m app.api_flask


Server will start at:
👉 http://127.0.0.1:8000

🌐 API Endpoints
🩺 Health Check
GET /health


Response:

{
  "status": "healthy",
  "timestamp": "2025-10-06T12:00:00Z"
}

📊 Status (System Info + Metrics Summary)
GET /status

📈 Prometheus-style Metrics
GET /metrics

💬 Ask a Question (RAG Answer)
POST /rag/answer
Content-Type: application/json

{
  "query": "When are Team Matching sessions and is it mandatory?",
  "k": 4
}


Response (example):

{
  "answer": "Team Matching sessions occur in Week 2 and Week 4. Participation is mandatory.",
  "contexts": [...],
  "meta": {
    "k": 4,
    "provider": "azure",
    "processing_time_ms": 312.58,
    "request_id": "a3b4f7c1"
  }
}

🔍 Search Context Chunks
POST /rag/search
Content-Type: application/json

{
  "query": "Team Matching",
  "k": 4
}


Response (example):

[
  {
    "id": "chunk_001",
    "score": 0.92,
    "source": "student_handbook.pdf"
  },
  ...
]

🐳 Docker Deployment
1️⃣ Create Docker Image
docker build -t rag-backend .

2️⃣ Run the Container
docker run -p 8000:8000 --env-file .env rag-backend


The backend will be accessible at:
👉 http://localhost:8000

🧾 Logs & Monitoring

Logs are stored in the logs/ directory.

View logs:

cat logs/app.log


Stream logs live:

tail -f logs/app.log

✅ Quick Test Commands
# Health check
curl http://localhost:8000/health

# Status with metrics
curl http://localhost:8000/status

# RAG query
curl -X POST http://localhost:8000/rag/answer \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"When are team matching sessions?\", \"k\": 4}"

🧠 Author Notes

This backend includes:

Structured logging (logs/app.log)

Observability headers (X-Request-ID, X-Response-Time)

Graceful error handling with unique request IDs

Dockerized runtime for fast local + cloud testing
