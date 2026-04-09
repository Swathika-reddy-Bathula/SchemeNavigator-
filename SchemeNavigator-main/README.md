# Scheme Navigator

Scheme Navigator is a full-stack RAG chatbot for Karnataka agriculture schemes.

- Backend: FastAPI + LangGraph + LangChain
- Vector DB: Astra DB
- LLM: Groq (`meta-llama/llama-4-scout-17b-16e-instruct`)
- Frontend: React + Vite

## Features

- Ask scheme-related questions against your ingested knowledge base
- Multi-turn chat with conversation memory
- Conversation history APIs (list, view, rename, delete)
- Simple health endpoint for frontend status checks
- JSONL interaction logging

## Project Structure

```text
.
├── app.py                  # FastAPI app and REST endpoints
├── Graph/pipeline.py       # LangGraph RAG pipeline
├── LLM/llm.py              # Groq chat client
├── Memory/                 # Conversation memory helper
├── History/                # File-based chat history store
├── Data/ingestion.py       # Astra DB ingestion script
├── frontend/               # React + Vite UI
├── .env.example            # Backend environment template
└── frontend/.env.example   # Frontend environment template
```

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- Astra DB account and collection access
- Groq API key

## Backend Setup

1. Create and activate a virtual environment.
2. Install Python dependencies.
3. Create `.env` from `.env.example`.
4. Start the API server.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env` in project root:

```env
GROQ_API_KEY=replace_with_your_groq_api_key
ASTRA_DB_ENDPOINT=https://your-database-id-your-region.apps.astra.datastax.com
ASTRA_DB_TOKEN=AstraCS:replace_with_your_astra_db_application_token
ASTRA_DB_COLLECTION=Schemes
LOG_FILE=interactions_log.jsonl
```

Run backend:

```bash
uvicorn app:app --reload
```

Backend default URL: `http://127.0.0.1:8000`

## Frontend Setup

1. Go to the `frontend` folder.
2. Install npm dependencies.
3. Create `frontend/.env` from `frontend/.env.example`.
4. Run Vite dev server.

```bash
cd frontend
npm install
```

`frontend/.env`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Run frontend:

```bash
npm run dev
```

## Ingest Data into Astra DB

Place source documents under `Translated/Ingestion` (as expected by `Data/ingestion.py`), then run:

```bash
python Data/ingestion.py
```

## API Endpoints

- `GET /status` - API health/status
- `POST /start` - Start a new conversation
- `POST /continue` - Continue an existing conversation
- `GET /history` - List all conversations
- `GET /history/{user_id}` - Get one conversation
- `PUT /history/{user_id}` - Update conversation title
- `DELETE /history/{user_id}` - Delete conversation

## Request Examples

Start:

```json
{
  "user_query": "What subsidy is available for drip irrigation?"
}
```

Continue:

```json
{
  "user_id": "your-conversation-id",
  "user_query": "Can you summarize eligibility criteria?"
}
```

## Notes

- `chat_history.json` and `interactions_log.jsonl` are runtime files and should not be committed.
- Keep `.env` out of Git. Commit only `.env.example`.
- Ignore generated folders like `.venv`, `frontend/node_modules`, `frontend/dist`, and `__pycache__`.


