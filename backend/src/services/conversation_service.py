"""
Conversation service for managing chat history and context.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import json

from ..models.search import ConversationMessage
from ..core.config import Config

logger = logging.getLogger(__name__)

class ConversationService:
    """Service for managing conversation history and context."""
    
    def __init__(self):
        self.connection = None
        self._connect()
        self._ensure_tables()
    
    def _connect(self):
        """Connect to PostgreSQL database."""
        try:
            self.connection = psycopg2.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD
            )
            logger.info("[OK] Conversation service connected to PostgreSQL!")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def _ensure_tables(self):
        """Create conversation tables if they don't exist."""
        try:
            with self.connection.cursor() as cursor:
                # Create conversations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id SERIAL PRIMARY KEY,
                        conversation_id VARCHAR(255) UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        title VARCHAR(500),
                        summary TEXT
                    )
                """)
                
                # Create conversation_messages table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_messages (
                        id SERIAL PRIMARY KEY,
                        conversation_id VARCHAR(255) NOT NULL,
                        message_type VARCHAR(20) NOT NULL CHECK (message_type IN ('user', 'assistant')),
                        content TEXT NOT NULL,
                        sources JSONB,
                        tokens_used INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conv_messages_conv_id 
                    ON conversation_messages(conversation_id, created_at DESC)
                """)
                
                self.connection.commit()
                logger.info("[OK] Conversation tables ensured!")
        except Exception as e:
            logger.error(f"Failed to create conversation tables: {e}")
            self.connection.rollback()
            raise
    
    def create_conversation(self, title: Optional[str] = None) -> str:
        """Create a new conversation and return its ID."""
        try:
            conversation_id = str(uuid.uuid4())
            
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO conversations (conversation_id, title)
                    VALUES (%s, %s)
                """, (conversation_id, title or "New Conversation"))
                
                self.connection.commit()
                logger.info(f"Created new conversation: {conversation_id}")
                return conversation_id
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            self.connection.rollback()
            raise
    
    def add_message(self, message: ConversationMessage) -> int:
        """Add a message to the conversation."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO conversation_messages 
                    (conversation_id, message_type, content, sources, tokens_used)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    message.conversation_id,
                    message.message_type,
                    message.content,
                    json.dumps(message.sources) if message.sources else None,
                    message.tokens_used
                ))
                
                message_id = cursor.fetchone()[0]
                
                # Update conversation timestamp
                cursor.execute("""
                    UPDATE conversations 
                    SET updated_at = CURRENT_TIMESTAMP 
                    WHERE conversation_id = %s
                """, (message.conversation_id,))
                
                self.connection.commit()
                return message_id
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            self.connection.rollback()
            raise
    
    def get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[ConversationMessage]:
        """Get recent messages from a conversation."""
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, conversation_id, message_type, content, sources, tokens_used,
                           created_at as timestamp
                    FROM conversation_messages
                    WHERE conversation_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (conversation_id, limit))
                
                rows = cursor.fetchall()
                messages = []
                
                for row in reversed(rows):  # Reverse to get chronological order
                    messages.append(ConversationMessage(
                        id=row['id'],
                        conversation_id=row['conversation_id'],
                        message_type=row['message_type'],
                        content=row['content'],
                        sources=row['sources'] if row['sources'] else None,
                        tokens_used=row['tokens_used'],
                        timestamp=row['timestamp'].isoformat() if row['timestamp'] else None
                    ))
                
                return messages
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    def format_conversation_context(self, messages: List[ConversationMessage]) -> str:
        """Format conversation history for LLM context."""
        if not messages:
            return ""
        
        context = "CONVERSATION HISTORY:\n"
        for message in messages[-10:]:  # Last 10 messages
            role = "User" if message.message_type == "user" else "Assistant"
            context += f"{role}: {message.content}\n"
        
        context += "\nCURRENT QUESTION:\n"
        return context
    
    def update_conversation_title(self, conversation_id: str, title: str):
        """Update conversation title based on the first question."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE conversations 
                    SET title = %s 
                    WHERE conversation_id = %s
                """, (title[:500], conversation_id))  # Limit title length
                
                self.connection.commit()
        except Exception as e:
            logger.error(f"Failed to update conversation title: {e}")
            self.connection.rollback()
    
    def conversation_exists(self, conversation_id: str) -> bool:
        """Check if a conversation exists."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 1 FROM conversations WHERE conversation_id = %s
                """, (conversation_id,))
                
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check conversation existence: {e}")
            return False
    
    def get_conversation_stats(self, conversation_id: str) -> Dict[str, Any]:
        """Get statistics for a conversation."""
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as message_count,
                        SUM(CASE WHEN message_type = 'user' THEN 1 ELSE 0 END) as user_messages,
                        SUM(CASE WHEN message_type = 'assistant' THEN 1 ELSE 0 END) as assistant_messages,
                        SUM(tokens_used) as total_tokens,
                        MIN(created_at) as first_message,
                        MAX(created_at) as last_message
                    FROM conversation_messages
                    WHERE conversation_id = %s
                """, (conversation_id,))
                
                return dict(cursor.fetchone() or {})
        except Exception as e:
            logger.error(f"Failed to get conversation stats: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check conversation service health."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM conversations")
                conversation_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM conversation_messages")
                message_count = cursor.fetchone()[0]
            
            return {
                "connected": True,
                "total_conversations": conversation_count,
                "total_messages": message_count
            }
        except Exception as e:
            logger.error(f"Conversation service health check failed: {e}")
            return {
                "connected": False,
                "error": str(e)
            }
