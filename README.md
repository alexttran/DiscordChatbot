# Discord RAG Backend — Working RAG + Azure Foundry Integration

This backend powers the Discord RAG chatbot. It uses:
- **FAISS vector store** for retrieval  
- **Azure AI Foundry (DeepSeek-R1 deployment)** for answer generation  
- A simple **Flask API** to serve `/rag/answer` and `/rag/search` endpoints  

---

##  Setup

1. **Clone the repo**  
   ```bash
   git clone https://github.com/alexttran/DiscordChatbot.git
   cd DiscordChatbot
   ```

2. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment variables**  
   Create a `.env` file in the project root (next to `requirements.txt`):  
   ```ini
   AZURE_OPENAI_ENDPOINT=https://aifoundary-rag.services.ai.azure.com
   AZURE_OPENAI_API_KEY=your-key-here
   AZURE_OPENAI_API_VERSION=2024-05-01-preview
   AZURE_OPENAI_MODEL=DeepSeek-R1
   ```

---

##  Run locally

```bash
python -m app.api_flask
```

Server runs at:  
`http://127.0.0.1:8000`

---

## API Endpoints

### Health check
```http
GET /health
```
Response:
```json
{ "ok": true }
```

### Ask a question
```http
POST /rag/answer
Content-Type: application/json

{
  "query": "When are Team Matching sessions and is it mandatory?",
  "k": 4
}
```
Response (example):
```json
{
  "answer": "Team Matching sessions occur in Week 2 and Week 4. Participation is mandatory.",
  "contexts": [...],
  "meta": {...}
}
```

### Search context chunks
```http
POST /rag/search
Content-Type: application/json

{
  "query": "Team Matching",
  "k": 4
}
```

---


