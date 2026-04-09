import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_astradb import AstraDBVectorStore
from dotenv import load_dotenv

# Import Pydantic for defining the state schema
from pydantic import BaseModel, Field, ConfigDict
from LLM.llm import LLMClient
from Memory import SimpleConversationMemory

load_dotenv()

ASTRA_DB_COLLECTION = os.getenv("ASTRA_DB_COLLECTION", "Schemes")


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing {name}. Add it to your .env file before starting the API.")
    return value

class AstraDBRetriever:
    def __init__(self):
        # Embedding model (LangChain wrapper)
        self.embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        # Vector Store setup
        self.vectorstore = AstraDBVectorStore(
            embedding=self.embedding_model,
            collection_name=ASTRA_DB_COLLECTION,
            api_endpoint=get_required_env("ASTRA_DB_ENDPOINT"),
            token=get_required_env("ASTRA_DB_TOKEN"),
        )
        print("Initialized AstraDBVectorStore")

    def get_relevant_documents(self, query: str):
        """Retrieve relevant documents from the Astra DB vector store."""
        print(f"Retrieving documents for query: '{query}'")
        return self.vectorstore.as_retriever().invoke(query)

# ---------- Config and Utility for logging ----------
LOG_FILE = Path(os.getenv("LOG_FILE", "interactions_log.jsonl"))
LOG_FILE.parent.mkdir(exist_ok=True, parents=True)

def log_interaction(record: Dict[str, Any]):
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except IOError as e:
        print(f"Error: Could not log interaction. Reason: {e}")

# ---------- LLM Client and Retriever initialization ----------
llm_client = None
retriever = None


def get_llm_client() -> LLMClient:
    global llm_client
    if llm_client is None:
        llm_client = LLMClient()
    return llm_client


def get_retriever() -> AstraDBRetriever:
    global retriever
    if retriever is None:
        retriever = AstraDBRetriever()
    return retriever

# ---------- Pydantic Model for State Schema ----------
class State(BaseModel):
    # This configuration allows Pydantic to handle custom classes
    # like AstraDBRetriever and ConversationBufferMemory.
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    user_id: str
    user_query: str
    retriever: AstraDBRetriever
    memory: SimpleConversationMemory
    normalized_query: str = ""
    retrieved: List[Dict[str, Any]] = Field(default_factory=list)
    constructed_prompt: str = ""
    answer: str = ""
    final_answer: str = ""
    retrieval_error: Optional[str] = None

# ---------- Prompt template ----------
PROMPT_TEMPLATE = (
    "You are an assistant knowledgeable in Karnataka agriculture schemes.\n"
    "Conversation so far:\n{prev_conversation}\n\n"
    "Here are relevant document excerpts (with ids):\n{sources}\n"
    "User question: {query}\n\n"
    "Answer clearly, cite using [id]. If unsure, say you cannot find authoritative source and suggest next steps."
)

# ---------- LangGraph Node definitions ----------
def node_decide(state: State) -> Dict[str, Any]:
    return {"normalized_query": state.user_query}

def node_retrieve(state: State) -> Dict[str, Any]:
    retriever_obj = state.retriever
    if not retriever_obj:
        raise ValueError("Retriever object not found in state.")

    try:
        docs = retriever_obj.get_relevant_documents(state.normalized_query)
    except Exception as exc:
        return {
            "retrieved": [],
            "retrieval_error": f"Document retrieval failed: {exc}"
        }

    retrieved = []
    for d in docs[:6]:
        metadata = getattr(d, "metadata", {}) or {}
        text = getattr(d, "page_content", "")
        retrieved.append({"id": metadata.get("id", "unknown"), "text": text, "metadata": metadata})
    return {"retrieved": retrieved}

def node_build_context(state: State) -> Dict[str, Any]:
    memory = state.memory
    conversation_history = memory.load_memory_variables({})['history']
    
    prev_conversation = "\n".join([
        f"User: {msg.content}" if isinstance(msg, HumanMessage) else f"Assistant: {msg.content}"
        for msg in conversation_history
    ])
    
    if state.retrieval_error:
        sources = f"Retriever error: {state.retrieval_error}\n"
    elif state.retrieved:
        sources = ""
        for d in state.retrieved:
            sid = d.get("id", "unknown")
            snippet = d.get("text", "")[:300].replace("\n", " ")
            sources += f"[{sid}] {snippet}...\n"
    else:
        sources = "No relevant Astra DB matches were found for this question.\n"
        
    return {"constructed_prompt": PROMPT_TEMPLATE.format(
        prev_conversation=prev_conversation,
        sources=sources,
        query=state.normalized_query
    )}

def node_generate_answer(state: State) -> Dict[str, Any]:
    prompt = state.constructed_prompt
    resp = get_llm_client().run_chat(system_message="You are an assistant.", user_message=prompt)
    return {"answer": resp}

def node_finalize(state: State) -> Dict[str, Any]:
    user_id = state.user_id
    normalized_query = state.normalized_query
    answer = state.answer
    memory = state.memory
    
    if normalized_query and answer:
        memory.save_context({"input": normalized_query}, {"output": answer})
    
    log_interaction({
        "ts": time.time(),
        "user_id": user_id,
        "query": normalized_query,
        "answer": answer,
        "retrieved_ids": [d.get("id") for d in state.retrieved],
        "retrieval_error": state.retrieval_error
    })
    return {"final_answer": answer}

# ---------- Graph builder and runner ----------
def build_graph() -> StateGraph:
    # Pass the state schema to the StateGraph constructor
    g = StateGraph(State)
    g.add_node("decide", node_decide)
    g.add_node("retrieve", node_retrieve)
    g.add_node("build_context", node_build_context)
    g.add_node("generate_answer", node_generate_answer)
    g.add_node("finalize", node_finalize)

    g.add_edge(START, "decide")
    g.add_edge("decide", "retrieve")
    g.add_edge("retrieve", "build_context")
    g.add_edge("build_context", "generate_answer")
    g.add_edge("generate_answer", "finalize")
    g.add_edge("finalize", END)
    return g

def run_query(graph: StateGraph, retriever_obj, user_id: str, user_query: str, memory: SimpleConversationMemory) -> Dict[str, Any]:
    init_state = State(
        user_id=user_id, 
        user_query=user_query, 
        retriever=retriever_obj or get_retriever(),
        memory=memory
    )
    result = graph.invoke(init_state)
    return result

rag_graph = build_graph().compile()
