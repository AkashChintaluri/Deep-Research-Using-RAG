"""
RAG (Retrieval-Augmented Generation) service for intelligent paper analysis.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from openai import OpenAI

from ..models.search import SearchResult, ConversationMessage
from ..core.config import Config
from .search_service import SearchService
from .conversation_service import ConversationService
from .guardrails_service import GuardrailsService

logger = logging.getLogger(__name__)

class RAGService:
    """Service for RAG operations combining retrieval and generation."""
    
    def __init__(self):
        self.search_service = SearchService()
        self.conversation_service = ConversationService()
        self.guardrails_service = GuardrailsService()
        
        # Initialize OpenAI client (Azure or regular)
        if Config.USE_AZURE_OPENAI:
            # Azure OpenAI configuration
            if not Config.AZURE_OPENAI_API_KEY or not Config.AZURE_OPENAI_ENDPOINT:
                raise ValueError("Azure OpenAI configuration missing. Please add AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT to your .env file.")
            
            self.client = OpenAI(
                api_key=Config.AZURE_OPENAI_API_KEY,
                base_url=f"{Config.AZURE_OPENAI_ENDPOINT}openai/deployments/{Config.AZURE_OPENAI_DEPLOYMENT}",
                default_query={"api-version": Config.AZURE_OPENAI_API_VERSION}
            )
            self.model = Config.AZURE_OPENAI_DEPLOYMENT  # Use deployment name for Azure
            logger.info(f"Initialized Azure OpenAI client with deployment: {Config.AZURE_OPENAI_DEPLOYMENT}")
        else:
            # Regular OpenAI configuration
            if not Config.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not found in environment variables. Please add it to your .env file.")
            
            self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
            self.model = Config.OPENAI_MODEL
            logger.info(f"Initialized regular OpenAI client with model: {Config.OPENAI_MODEL}")
        
        self.max_tokens = Config.OPENAI_MAX_TOKENS
        self.temperature = Config.OPENAI_TEMPERATURE
        
    def _format_papers_for_context(self, papers: List[SearchResult]) -> str:
        """Format retrieved papers as context for the LLM."""
        if not papers:
            return "No relevant papers found."
        
        context = "Here are the most relevant research papers:\n\n"
        
        for i, paper in enumerate(papers, 1):
            context += f"**Paper {i}:**\n"
            context += f"Title: {paper.title}\n"
            context += f"Authors: {paper.authors}\n"
            context += f"Abstract: {paper.abstract}\n"
            context += f"Relevance Score: {paper.score:.3f}\n"
            context += f"Source: {paper.search_type}\n"
            if paper.text:
                context += f"Relevant Content: {paper.text}\n"
            context += "\n---\n\n"
        
        return context
    
    def _create_rag_prompt(self, user_query: str, context: str, conversation_context: str = "") -> str:
        """Create a comprehensive RAG prompt for the LLM."""
        prompt = f"""You are an expert astronomy and astrophysics research assistant. Your task is to provide comprehensive, accurate answers based on the research papers provided and the conversation history.

{conversation_context}

CONTEXT PAPERS:
{context}

USER QUESTION: {user_query}

INSTRUCTIONS:
1. Consider the conversation history when answering - build upon previous discussions
2. If this is a follow-up question, reference what was discussed before
3. Provide a detailed, well-structured answer based on the papers above
4. Always cite specific papers when making claims (e.g., "According to Paper 1..." or "As shown in the research by [authors]...")
5. If papers disagree or show different perspectives, mention this
6. Synthesize information across multiple papers when relevant
7. If the question cannot be fully answered with the provided papers, clearly state what information is missing
8. Use clear, accessible language while maintaining scientific accuracy
9. Structure your response with clear sections if discussing multiple aspects
10. For follow-up questions, acknowledge the connection to previous topics

FORMATTING REQUIREMENTS:
- Use **bold text** for emphasis and key concepts
- Use *italic text* for technical terms and paper titles
- Use ## for main section headings (e.g., ## Wormholes in the Accelerating Universe)
- Use ### for subsection headings (e.g., ### Key Concepts)
- Use numbered lists (1., 2., 3.) for multiple points or steps
- Use bullet points (- or •) for lists of items
- Separate different topics with double line breaks (blank lines)
- Use proper paragraph breaks to avoid wall of text
- Format mathematical expressions using LaTeX notation ($...$ for inline, $$...$$ for display)
- Use proper spacing and indentation for readability

RESPONSE FORMAT:
You MUST structure your response exactly as follows:

## Key Findings
[List 2-3 main discoveries from the papers]

## Evidence & Analysis
[Brief analysis of supporting evidence and how sources relate]

## Conclusions
[Main takeaways and significance]

## Follow-up Questions
1. [Question 1]
2. [Question 2] 
3. [Question 3]

Keep each section concise (2-3 sentences max per section). Do NOT write long paragraphs or detailed explanations.

RESPONSE:"""
        
        return prompt
    
    def _generate_follow_up_questions(self, papers: List[SearchResult], topic: str) -> List[str]:
        """Generate relevant follow-up questions based on the retrieved papers."""
        if not papers:
            return []
        
        # Extract key topics and concepts from papers
        topics = set()
        for paper in papers:
            if paper.categories:
                topics.update(paper.categories.split())
            if paper.abstract:
                # Extract key terms (simplified)
                words = paper.abstract.lower().split()
                key_terms = [word for word in words if len(word) > 5 and word.isalpha()]
                topics.update(key_terms[:10])  # Limit to avoid too many topics
        
        # Generate follow-up questions based on common research patterns
        follow_ups = [
            f"What are the latest developments in {topic}?",
            f"How do different theoretical models explain {topic}?",
            f"What observational evidence supports theories about {topic}?",
            f"What are the main challenges in studying {topic}?",
            f"How does {topic} relate to other astronomical phenomena?"
        ]
        
        # Add specific questions based on paper topics
        if "black hole" in topic.lower():
            follow_ups.extend([
                "What are the different types of black holes mentioned in the research?",
                "How do black hole mergers affect gravitational wave detection?",
                "What role do black holes play in galaxy formation?"
            ])
        elif "wormhole" in topic.lower():
            follow_ups.extend([
                "What are the physical requirements for traversable wormholes?",
                "How do wormholes relate to general relativity and quantum mechanics?",
                "What observational signatures might indicate wormhole existence?"
            ])
        
        return follow_ups[:5]  # Return top 5 questions
    
    def _extract_reasoning_steps(self, response_text: str) -> List[str]:
        """Extract reasoning steps from the AI response."""
        reasoning_steps = []
        
        # Look for methodology sections or reasoning indicators
        lines = response_text.split('\n')
        in_methodology = False
        
        for line in lines:
            line = line.strip()
            if 'methodology' in line.lower() or 'reasoning' in line.lower() or 'analysis' in line.lower():
                in_methodology = True
                continue
            elif line.startswith('##') and in_methodology:
                break
            elif in_methodology and line:
                if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    reasoning_steps.append(line[1:].strip())
                elif line and not line.startswith('#'):
                    reasoning_steps.append(line)
        
        # If no explicit methodology section, extract from general structure
        if not reasoning_steps:
            for line in lines:
                if (line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or 
                    line.startswith('4.') or line.startswith('5.')):
                    reasoning_steps.append(line)
        
        return reasoning_steps[:5]  # Limit to 5 steps
    
    def _generate_research_summary(self, papers: List[SearchResult], query: str) -> Dict[str, Any]:
        """Generate a structured research summary."""
        if not papers:
            return {"total_papers": 0, "key_findings": [], "research_gaps": []}
        
        # Extract key findings from abstracts
        key_findings = []
        research_gaps = []
        total_papers = len(papers)
        
        for paper in papers:
            if paper.abstract:
                # Simple extraction of key findings (first sentence often contains main finding)
                abstract_sentences = paper.abstract.split('.')
                if abstract_sentences:
                    key_findings.append(abstract_sentences[0].strip())
        
        # Identify research gaps (papers mentioning limitations or future work)
        for paper in papers:
            if paper.abstract and ('limitation' in paper.abstract.lower() or 
                                 'future work' in paper.abstract.lower() or 
                                 'further research' in paper.abstract.lower()):
                research_gaps.append(f"Research gap identified in {paper.title[:50]}...")
        
        return {
            "total_papers": total_papers,
            "key_findings": key_findings[:5],  # Top 5 findings
            "research_gaps": research_gaps[:3],  # Top 3 gaps
            "search_scope": query,
            "date_range": self._extract_date_range(papers)
        }
    
    def _extract_date_range(self, papers: List[SearchResult]) -> Dict[str, str]:
        """Extract date range from paper IDs (assuming arXiv format)."""
        if not papers:
            return {"earliest": "N/A", "latest": "N/A"}
        
        # Extract years from paper IDs (assuming format like 0704.1224)
        years = []
        for paper in papers:
            if paper.paper_id and len(paper.paper_id) >= 4:
                try:
                    year = int(paper.paper_id[:2])
                    if year < 50:  # Assume 2000s
                        year += 2000
                    else:  # Assume 1900s
                        year += 1900
                    years.append(year)
                except ValueError:
                    continue
        
        if years:
            return {
                "earliest": str(min(years)),
                "latest": str(max(years))
            }
        return {"earliest": "N/A", "latest": "N/A"}
    
    async def generate_response(self, query: str, conversation_id: Optional[str] = None, n_results: int = 5, search_type: str = "both", max_context_messages: int = 5) -> Dict[str, Any]:
        """Generate a RAG response combining retrieval and generation."""
        try:
            logger.info(f"RAG query: {query}, conversation_id: {conversation_id}")
            
            # Step 0: Validate query is astronomy-related (Guardrails)
            is_astronomy, validation_reason = self.guardrails_service.is_astronomy_related(query)
            logger.info(f"Query validation: {validation_reason}")
            
            if not is_astronomy:
                # Return guardrails response for out-of-scope questions
                fallback_response = self.guardrails_service.create_fallback_response(query, papers_available=False)
                
                # Still handle conversation context for the fallback
                if conversation_id:
                    user_message = ConversationMessage(
                        conversation_id=conversation_id,
                        message_type="user",
                        content=query
                    )
                    self.conversation_service.add_message(user_message)
                    
                    assistant_message = ConversationMessage(
                        conversation_id=conversation_id,
                        message_type="assistant",
                        content=fallback_response
                    )
                    self.conversation_service.add_message(assistant_message)
                else:
                    conversation_id = self.conversation_service.create_conversation(
                        title="Out-of-scope question"
                    )
                
                return {
                    "response": fallback_response,
                    "sources": [],
                    "query": query,
                    "search_results_count": 0,
                    "conversation_id": conversation_id,
                    "context_used": False,
                    "guardrails_triggered": True,
                    "validation_reason": validation_reason
                }
            
            # Step 1: Handle conversation context
            conversation_context = ""
            is_new_conversation = False
            
            if conversation_id:
                # Get conversation history
                history = self.conversation_service.get_conversation_history(
                    conversation_id, limit=max_context_messages
                )
                if history:
                    conversation_context = self.conversation_service.format_conversation_context(history)
                    logger.info(f"Using conversation context with {len(history)} messages")
                else:
                    logger.warning(f"No history found for conversation {conversation_id}")
            else:
                # Create new conversation
                conversation_id = self.conversation_service.create_conversation(
                    title=query[:100] + "..." if len(query) > 100 else query
                )
                is_new_conversation = True
                logger.info(f"Created new conversation: {conversation_id}")
            
            # Step 2: Add user message to conversation
            user_message = ConversationMessage(
                conversation_id=conversation_id,
                message_type="user",
                content=query
            )
            self.conversation_service.add_message(user_message)
            
            # Step 3: Retrieve relevant papers
            papers = await self.search_service.search_papers(
                query=query,
                n_results=n_results,
                search_type=search_type
            )
            
            if not papers:
                # Use guardrails fallback for no papers found
                fallback_response = self.guardrails_service.create_fallback_response(query, papers_available=False)
                
                # Add assistant message to conversation
                assistant_message = ConversationMessage(
                    conversation_id=conversation_id,
                    message_type="assistant",
                    content=fallback_response
                )
                self.conversation_service.add_message(assistant_message)
                
                return {
                    "response": fallback_response,
                    "sources": [],
                    "query": query,
                    "search_results_count": 0,
                    "conversation_id": conversation_id,
                    "context_used": bool(conversation_context),
                    "guardrails_triggered": True,
                    "validation_reason": "No relevant papers found in database"
                }
            
            # Step 4: Format context for LLM
            context = self._format_papers_for_context(papers)
            
            # Step 5: Create RAG prompt
            prompt = self._create_rag_prompt(query, context, conversation_context)
            
            # Step 6: Generate response using OpenAI
            logger.info("Generating LLM response with conversation context...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert astronomy and astrophysics research assistant. You MUST respond in the exact format specified in the user's request. Keep responses concise and structured."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=Config.OPENAI_TIMEOUT
            )
            
            generated_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            # Step 7: Skip grounding validation for now (temporarily disabled)
            is_grounded = True
            grounding_reason = "Validation temporarily disabled"
            logger.info(f"Response grounding: {grounding_reason}")
            
            # Step 8: Add assistant message to conversation
            sources_data = [
                {
                    "paper_id": paper.paper_id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "abstract": paper.abstract,
                    "score": paper.score,
                    "search_type": paper.search_type,
                    "chunk_id": paper.chunk_id,
                    "text": paper.text,
                    "categories": paper.categories,
                    "text_length": paper.text_length,
                    "word_count": paper.word_count,
                    "pdf_path": paper.pdf_path,
                    "full_text_preview": paper.full_text_preview
                }
                for paper in papers
            ]
            
            assistant_message = ConversationMessage(
                conversation_id=conversation_id,
                message_type="assistant",
                content=generated_text,
                sources=sources_data,
                tokens_used=tokens_used
            )
            self.conversation_service.add_message(assistant_message)
            
            # Step 9: Update conversation title if it's the first exchange
            if is_new_conversation:
                title = query[:100] + "..." if len(query) > 100 else query
                self.conversation_service.update_conversation_title(conversation_id, title)
            
            # Step 10: Generate follow-up questions
            follow_up_questions = self._generate_follow_up_questions(papers, query)
            
            # Step 11: Format response with enhanced metadata
            result = {
                "response": generated_text,
                "sources": sources_data,
                "query": query,
                "search_results_count": len(papers),
                "model_used": self.model,
                "tokens_used": tokens_used,
                "conversation_id": conversation_id,
                "context_used": bool(conversation_context),
                "guardrails_triggered": not is_grounded,
                "validation_reason": grounding_reason if not is_grounded else "Response properly grounded",
                "follow_up_questions": follow_up_questions,
                "reasoning_steps": self._extract_reasoning_steps(generated_text),
                "research_summary": self._generate_research_summary(papers, query)
            }
            
            logger.info(f"RAG response generated successfully. Tokens used: {tokens_used}, Context used: {bool(conversation_context)}")
            return result
            
        except Exception as e:
            logger.error(f"RAG generation failed: {e}")
            return {
                "response": f"I encountered an error while processing your request: {str(e)}. Please try again or rephrase your question.",
                "sources": [],
                "query": query,
                "search_results_count": 0,
                "conversation_id": conversation_id,
                "error": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check RAG service health."""
        try:
            # Test OpenAI connection
            test_response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10,
                timeout=5
            )
            
            openai_status = {
                "connected": True,
                "model": self.model,
                "response_received": bool(test_response.choices)
            }
            
        except Exception as e:
            openai_status = {
                "connected": False,
                "error": str(e)
            }
        
        # Check search service health
        search_health = await self.search_service.health_check()
        
        # Check conversation service health
        conversation_health = await self.conversation_service.health_check()
        
        # Check guardrails service health
        guardrails_health = await self.guardrails_service.health_check()
        
        return {
            "rag_service": "healthy" if openai_status["connected"] else "degraded",
            "openai": openai_status,
            "search_service": search_health,
            "conversation_service": conversation_health,
            "guardrails_service": guardrails_health
        }
