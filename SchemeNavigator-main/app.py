# app.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
from uuid import uuid4
import time # <-- Added import for timestamp
from pydantic import BaseModel # <-- Added import for response model

# Import the LangGraph components from our new graph.py file
from Graph.pipeline import rag_graph, get_retriever, run_query
from History import HistoryStore
from Memory import SimpleConversationMemory
from langchain_core.messages import AIMessage, HumanMessage
# This import seems unused in this file, but keeping it as requested
from LLM.llm import LLMClient

# ---------- FastAPI App ----------
app = FastAPI(title="LangGraph RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global dictionary to manage memory for multiple users
user_memories: Dict[str, SimpleConversationMemory] = {}
history_store = HistoryStore()


# ---------- ADDED SECTION: The missing /status endpoint ----------
# This response model ensures our status endpoint has a consistent structure
class StatusResponse(BaseModel):
    status: str
    timestamp: float


class MessageResponse(BaseModel):
    role: str
    content: str
    timestamp: float


class ConversationSummaryResponse(BaseModel):
    user_id: str
    title: str
    created_at: float
    updated_at: float
    message_count: int


class ConversationDetailResponse(ConversationSummaryResponse):
    messages: List[MessageResponse]


class UpdateConversationRequest(BaseModel):
    title: str


def format_conversation_detail(conversation: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **conversation,
        "message_count": len(conversation.get("messages", [])),
    }


def build_memory_from_history(messages: List[Dict[str, Any]]) -> SimpleConversationMemory:
    memory = SimpleConversationMemory(return_messages=True)
    for message in messages:
        role = message.get("role")
        content = message.get("content", "")
        if role == "user":
            memory.history.append(HumanMessage(content=content))
        elif role == "assistant":
            memory.history.append(AIMessage(content=content))
    return memory

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """A simple endpoint for the frontend to check if the server is running."""
    return {"status": "ok", "timestamp": time.time()}
# ----------------------------------------------------------------


@app.get("/history", response_model=List[ConversationSummaryResponse])
async def list_history():
    return history_store.list_conversations()


@app.get("/history/{user_id}", response_model=ConversationDetailResponse)
async def get_history(user_id: str):
    conversation = history_store.get_conversation(user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return format_conversation_detail(conversation)


@app.post("/history/{user_id}", response_model=ConversationDetailResponse)
async def create_history_entry(user_id: str, request: Dict[str, str]):
    initial_message = request.get("initial_message", "")
    if history_store.get_conversation(user_id):
        raise HTTPException(status_code=409, detail="Conversation already exists.")
    conversation = history_store.create_conversation(user_id, initial_message)
    return format_conversation_detail(conversation)


@app.put("/history/{user_id}", response_model=ConversationDetailResponse)
async def update_history(user_id: str, request: UpdateConversationRequest):
    try:
        conversation = history_store.update_conversation(user_id, request.title)
        return format_conversation_detail(conversation)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/history/{user_id}")
async def delete_history(user_id: str):
    deleted = history_store.delete_conversation(user_id)
    user_memories.pop(user_id, None)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"status": "deleted", "user_id": user_id}


# POST /start (starts a new conversation)
@app.post("/start")
async def start_conversation(request: Dict[str, str]):
    """Starts a new conversation session, generating a new user ID."""
    global user_memories
    
    user_query = request.get("user_query")
    if not user_query:
        raise HTTPException(status_code=400, detail="'user_query' is required.")

    user_id = str(uuid4())
    user_memories[user_id] = SimpleConversationMemory(return_messages=True)
    history_store.create_conversation(user_id, user_query)
    history_store.append_message(user_id, "user", user_query)

    try:
        output = run_query(rag_graph, get_retriever(), user_id, user_query, user_memories[user_id])
    except ValueError as exc:
        history_store.delete_conversation(user_id)
        user_memories.pop(user_id, None)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        history_store.delete_conversation(user_id)
        user_memories.pop(user_id, None)
        raise HTTPException(status_code=500, detail=f"Failed to process query: {exc}") from exc

    assistant_response = output.get("final_answer", "Sorry, something went wrong.")
    history_store.append_message(user_id, "assistant", assistant_response)
    
    return {
        "message": assistant_response,
        "user_id": user_id
    }

# POST /continue (adds a follow-up turn)
@app.post("/continue")
async def continue_conversation(request: Dict[str, str]):
    """Continues an existing conversation session using the provided user ID."""
    global user_memories
    
    user_id = request.get("user_id")
    user_query = request.get("user_query")

    if not user_id or not user_query:
        raise HTTPException(status_code=400, detail="'user_id' and 'user_query' are required.")

    if user_id not in user_memories:
        conversation = history_store.get_conversation(user_id)
        if not conversation:
            raise HTTPException(
                status_code=404, 
                detail="User session not found. Please start a new conversation."
            )
        user_memories[user_id] = build_memory_from_history(conversation.get("messages", []))
    
    memory = user_memories[user_id]
    history_store.append_message(user_id, "user", user_query)
    
    try:
        output = run_query(rag_graph, get_retriever(), user_id, user_query, memory)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process query: {exc}") from exc

    assistant_response = output.get("final_answer", "Sorry, something went wrong.")
    history_store.append_message(user_id, "assistant", assistant_response)
    
    return {
        "message": assistant_response,
        "user_id": user_id
    }

# To run the application:
# Run the server from your terminal: `uvicorn app:app --reload`
