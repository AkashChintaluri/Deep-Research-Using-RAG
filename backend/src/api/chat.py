"""
Chat API endpoints for RAG-powered conversations.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
import logging

from src.models.search import ChatRequest, ChatResponse, ConversationRequest, ExportRequest
from src.services.rag_service import RAGService
from src.services.export_service import ExportService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["chat"])

# Initialize services
rag_service = RAGService()
export_service = ExportService()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_papers(request: ConversationRequest):
    """Chat with papers using RAG with conversation memory."""
    try:
        result = await rag_service.generate_response(
            query=request.query,
            conversation_id=request.conversation_id,
            n_results=request.n_results,
            search_type=request.search_type,
            max_context_messages=request.max_context_messages
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        logger.error(f"Chat request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat request failed: {e}")

@router.get("/chat", response_model=ChatResponse)
async def chat_with_papers_get(
    query: str = Query(..., description="Your question about the research papers"),
    conversation_id: str = Query(None, description="Conversation ID for context"),
    n_results: int = Query(5, description="Number of papers to retrieve for context"),
    search_type: str = Query("both", description="Search type: postgres, pinecone, or both"),
    max_context_messages: int = Query(5, description="Maximum context messages to include")
):
    """Chat with papers using GET method for easy testing."""
    try:
        result = await rag_service.generate_response(
            query=query,
            conversation_id=conversation_id,
            n_results=n_results,
            search_type=search_type,
            max_context_messages=max_context_messages
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        logger.error(f"Chat request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat request failed: {e}")

@router.get("/chat/history/{conversation_id}")
async def get_conversation_history(
    conversation_id: str,
    limit: int = Query(20, description="Maximum number of messages to return")
):
    """Get conversation history for a specific conversation."""
    try:
        history = rag_service.conversation_service.get_conversation_history(
            conversation_id, limit=limit
        )
        return {"conversation_id": conversation_id, "messages": history}
    except Exception as e:
        logger.error(f"Failed to get conversation history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation history: {e}")

@router.get("/chat/stats/{conversation_id}")
async def get_conversation_stats(conversation_id: str):
    """Get statistics for a specific conversation."""
    try:
        stats = rag_service.conversation_service.get_conversation_stats(conversation_id)
        return {"conversation_id": conversation_id, "stats": stats}
    except Exception as e:
        logger.error(f"Failed to get conversation stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation stats: {e}")

@router.get("/chat/health")
async def chat_health_check():
    """Health check for RAG chat service."""
    try:
        health_status = await rag_service.health_check()
        return health_status
    except Exception as e:
        logger.error(f"Chat health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat health check failed: {e}")

@router.post("/chat/export/markdown")
async def export_conversation_markdown(request: ExportRequest):
    """Export conversation to Markdown format."""
    try:
        conversation_id = request.conversation_id
        query = request.query
        
        if not conversation_id:
            raise HTTPException(status_code=400, detail="conversation_id is required")
        
        # Get conversation history
        history = rag_service.conversation_service.get_conversation_history(conversation_id)
        if not history:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get the latest assistant message with sources
        latest_message = None
        for message in reversed(history):
            if message.message_type == 'assistant' and message.sources:
                latest_message = message
                break
        
        if not latest_message:
            raise HTTPException(status_code=404, detail="No assistant response with sources found")
        
        # Export to markdown
        filepath = export_service.export_to_markdown(
            response=latest_message.content or '',
            sources=latest_message.sources or [],
            query=query,
            conversation_id=conversation_id,
            follow_up_questions=getattr(latest_message, 'follow_up_questions', None),
            reasoning_steps=getattr(latest_message, 'reasoning_steps', None),
            research_summary=getattr(latest_message, 'research_summary', None)
        )
        
        return FileResponse(
            path=filepath,
            media_type='text/markdown',
            filename=f"research_report_{conversation_id}.md"
        )
        
    except Exception as e:
        logger.error(f"Markdown export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Markdown export failed: {e}")

@router.post("/chat/export/pdf")
async def export_conversation_pdf(request: ExportRequest):
    """Export conversation to PDF format."""
    try:
        conversation_id = request.conversation_id
        query = request.query
        
        if not conversation_id:
            raise HTTPException(status_code=400, detail="conversation_id is required")
        
        # Check if any PDF generation is available
        from src.services.export_service import ExportService, REPORTLAB_AVAILABLE
        temp_export = ExportService()
        weasyprint_available = temp_export._check_weasyprint_availability()
        
        if not weasyprint_available and not REPORTLAB_AVAILABLE:
            raise HTTPException(
                status_code=503, 
                detail="PDF export is not available. No PDF generation libraries are installed. Please use Markdown export instead."
            )
        
        # Get conversation history
        history = rag_service.conversation_service.get_conversation_history(conversation_id)
        if not history:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get the latest assistant message with sources
        latest_message = None
        for message in reversed(history):
            if message.message_type == 'assistant' and message.sources:
                latest_message = message
                break
        
        if not latest_message:
            raise HTTPException(status_code=404, detail="No assistant response with sources found")
        
        # Export to PDF
        filepath = export_service.export_to_pdf(
            response=latest_message.content or '',
            sources=latest_message.sources or [],
            query=query,
            conversation_id=conversation_id,
            follow_up_questions=getattr(latest_message, 'follow_up_questions', None),
            reasoning_steps=getattr(latest_message, 'reasoning_steps', None),
            research_summary=getattr(latest_message, 'research_summary', None)
        )
        
        return FileResponse(
            path=filepath,
            media_type='application/pdf',
            filename=f"research_report_{conversation_id}.pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF export failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF export failed: {e}")

@router.get("/chat/exports")
async def list_exports():
    """List all available export files."""
    try:
        exports = export_service.list_exports()
        return {"exports": exports}
    except Exception as e:
        logger.error(f"Failed to list exports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list exports: {e}")

@router.delete("/chat/exports/{filename}")
async def delete_export(filename: str):
    """Delete an export file."""
    try:
        success = export_service.delete_export(filename)
        if success:
            return {"message": f"Export {filename} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Export file not found")
    except Exception as e:
        logger.error(f"Failed to delete export {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete export: {e}")
