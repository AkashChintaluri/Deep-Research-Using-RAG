"""
Search-related data models.
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class SearchRequest(BaseModel):
    query: str
    n_results: int = 5
    search_type: str = "faiss"  # "postgres", "faiss", "pinecone", or "both"

class SearchResult(BaseModel):
    paper_id: str
    title: str
    authors: str
    abstract: str
    score: float
    search_type: str
    chunk_id: Optional[str] = None
    text: Optional[str] = None
    categories: Optional[str] = None
    text_length: Optional[int] = None
    word_count: Optional[int] = None
    pdf_path: Optional[str] = None
    full_text_preview: Optional[str] = None

class DatabaseStats(BaseModel):
    total_papers: int
    papers_with_full_text: int
    average_text_length: int
    top_categories: List[Dict[str, Any]]

class ChatRequest(BaseModel):
    query: str
    n_results: int = 5
    search_type: str = "faiss"  # "postgres", "faiss", "pinecone", or "both"

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    query: str
    search_results_count: int
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None
    error: Optional[str] = None
    conversation_id: Optional[str] = None
    context_used: Optional[bool] = None
    guardrails_triggered: Optional[bool] = None
    validation_reason: Optional[str] = None

class ConversationMessage(BaseModel):
    id: Optional[int] = None
    conversation_id: str
    message_type: str  # "user" or "assistant"
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    timestamp: Optional[str] = None
    tokens_used: Optional[int] = None

class ConversationRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    n_results: int = 5
    search_type: str = "faiss"
    max_context_messages: int = 5

class ExportRequest(BaseModel):
    conversation_id: str
    query: str  # How many previous messages to include