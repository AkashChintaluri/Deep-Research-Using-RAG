"""
Guardrails service to ensure responses stay within scope of available data.
"""

import logging
import re
from typing import Dict, Any, List, Tuple
from openai import OpenAI

from ..core.config import Config

logger = logging.getLogger(__name__)

class GuardrailsService:
    """Service for implementing guardrails and content validation."""
    
    def __init__(self):
        # Initialize OpenAI client for classification (Azure or regular)
        try:
            if Config.USE_AZURE_OPENAI and Config.AZURE_OPENAI_API_KEY:
                self.client = OpenAI(
                    api_key=Config.AZURE_OPENAI_API_KEY,
                    base_url=f"{Config.AZURE_OPENAI_ENDPOINT}openai/deployments/{Config.AZURE_OPENAI_DEPLOYMENT}",
                    default_query={"api-version": Config.AZURE_OPENAI_API_VERSION}
                )
            elif Config.OPENAI_API_KEY:
                self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
            else:
                self.client = None
                logger.warning("No OpenAI client available for query validation")
        except Exception as e:
            self.client = None
            logger.warning(f"Failed to initialize OpenAI client for guardrails: {e}")
        
        # Define astronomy/astrophysics related keywords and topics
        self.astronomy_keywords = {
            'core_topics': [
                'black hole', 'blackhole', 'galaxy', 'galaxies', 'star', 'stars', 'stellar',
                'planet', 'planets', 'exoplanet', 'exoplanets', 'cosmic', 'universe',
                'astronomy', 'astrophysics', 'cosmology', 'gravitational', 'radiation',
                'telescope', 'observation', 'nebula', 'supernova', 'pulsar', 'quasar',
                'dark matter', 'dark energy', 'cosmic ray', 'space', 'celestial',
                'orbital', 'solar system', 'interstellar', 'intergalactic', 'redshift',
                'photometry', 'spectroscopy', 'luminosity', 'magnitude', 'flux'
            ],
            'physics_terms': [
                'gravity', 'gravitational', 'relativity', 'quantum', 'electromagnetic',
                'thermodynamics', 'nuclear fusion', 'nuclear reaction', 'particle physics',
                'magnetic field', 'electric field', 'wave', 'frequency', 'wavelength',
                'energy', 'mass', 'velocity', 'acceleration', 'temperature', 'pressure'
            ],
            'observational': [
                'hubble', 'chandra', 'spitzer', 'kepler', 'jwst', 'james webb',
                'radio telescope', 'x-ray', 'infrared', 'ultraviolet', 'optical',
                'gamma ray', 'observation', 'survey', 'catalog', 'data analysis'
            ]
        }
        
        # Topics that are clearly out of scope
        self.out_of_scope_patterns = [
            r'\b(cooking|recipe|food|restaurant)\b',
            r'\b(sports|football|basketball|soccer)\b',
            r'\b(politics|election|government|policy)\b',
            r'\b(medicine|doctor|hospital|drug|medication)\b',
            r'\b(business|marketing|sales|profit)\b',
            r'\b(programming|code|software|app|website)\b',
            r'\b(travel|vacation|hotel|flight)\b',
            r'\b(fashion|clothes|style|beauty)\b',
            r'\b(music|song|album|artist|band)\b',
            r'\b(movie|film|actor|actress|cinema)\b'
        ]
    
    def is_astronomy_related(self, query: str) -> Tuple[bool, str]:
        """Check if a query is related to astronomy/astrophysics."""
        query_lower = query.lower()
        
        # Check for obvious out-of-scope patterns
        for pattern in self.out_of_scope_patterns:
            if re.search(pattern, query_lower):
                topic = pattern.split('|')[0].strip('\\b()')
                return False, f"Query appears to be about {topic} which is outside the scope of astronomy research papers."
        
        # Check for astronomy keywords
        all_keywords = []
        for category in self.astronomy_keywords.values():
            all_keywords.extend(category)
        
        found_keywords = [kw for kw in all_keywords if kw in query_lower]
        
        if found_keywords:
            return True, f"Query contains astronomy-related terms: {', '.join(found_keywords[:3])}"
        
        # If no clear indicators, use LLM for classification (if available)
        if self.client:
            return self._llm_topic_classification(query)
        
        # Default to allowing if we can't determine (err on the side of trying)
        return True, "Query classification unclear, proceeding with search"
    
    def _llm_topic_classification(self, query: str) -> Tuple[bool, str]:
        """Use LLM to classify if query is astronomy-related."""
        try:
            classification_prompt = f"""
You are a topic classifier for an astronomy research database. Determine if the following query is related to astronomy, astrophysics, or space science.

Query: "{query}"

The database contains research papers about:
- Black holes, galaxies, stars, planets, exoplanets
- Cosmic phenomena, dark matter, dark energy
- Stellar evolution, galaxy formation
- Observational astronomy, telescopes, surveys
- Gravitational waves, cosmic rays
- Solar system objects, asteroids, comets
- Cosmology, universe structure and evolution

Respond with ONLY:
"ASTRONOMY" if the query is related to astronomy/astrophysics/space science
"NOT_ASTRONOMY" if the query is about other topics

Response:"""

            # Use appropriate model based on configuration
            model_name = Config.AZURE_OPENAI_DEPLOYMENT if Config.USE_AZURE_OPENAI else "gpt-3.5-turbo"
            
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": classification_prompt}],
                max_tokens=10,
                temperature=0.1,
                timeout=10
            )
            
            result = response.choices[0].message.content.strip().upper()
            
            if "ASTRONOMY" in result and "NOT_ASTRONOMY" not in result:
                return True, "LLM classified as astronomy-related"
            else:
                return False, "LLM classified as not astronomy-related"
                
        except Exception as e:
            logger.error(f"LLM topic classification failed: {e}")
            return True, "Classification failed, proceeding with search"
    
    def validate_response_grounding(self, response: str, papers_context: str) -> Tuple[bool, str]:
        """Validate that the response is grounded in the provided papers."""
        if not papers_context or not response:
            return False, "No papers or response to validate"
        
        # Check for citation patterns
        citation_patterns = [
            r'according to paper \d+',
            r'paper \d+ shows',
            r'as shown in.*paper',
            r'the research by.*shows',
            r'studies indicate',
            r'research shows',
            r'based on.*papers'
        ]
        
        has_citations = any(re.search(pattern, response.lower()) for pattern in citation_patterns)
        
        if not has_citations:
            return False, "Response lacks proper citations to provided papers"
        
        # Check for generic/non-specific statements that might indicate hallucination
        generic_phrases = [
            'it is well known that',
            'common knowledge',
            'everyone knows',
            'obviously',
            'clearly',
            'without a doubt',
            'it is universally accepted'
        ]
        
        has_generic = any(phrase in response.lower() for phrase in generic_phrases)
        
        if has_generic:
            return False, "Response contains generic statements not grounded in specific research"
        
        return True, "Response appears to be properly grounded"
    
    def create_strict_rag_prompt(self, query: str, context: str, conversation_context: str = "") -> str:
        """Create a RAG prompt with strict guardrails."""
        prompt = f"""You are a specialized astronomy and astrophysics research assistant. You MUST follow these strict rules:

CRITICAL RULES:
1. ONLY answer questions about astronomy, astrophysics, or space science
2. ONLY use information from the research papers provided below
3. NEVER use knowledge outside of the provided papers
4. If the papers don't contain enough information to answer, explicitly say so
5. ALWAYS cite specific papers when making claims
6. If the question is not astronomy-related, politely redirect to astronomy topics

{conversation_context}

RESEARCH PAPERS PROVIDED:
{context}

USER QUESTION: {query}

RESPONSE REQUIREMENTS:
- Start by checking if this is an astronomy/space science question
- If NOT astronomy-related: "I can only help with astronomy and astrophysics questions based on research papers. Please ask about topics like black holes, galaxies, stars, planets, or other astronomical phenomena."
- If astronomy-related but papers insufficient: Use the available papers to provide the best possible answer, even if incomplete. Structure the response as specified below.
- If astronomy-related with sufficient papers: Provide detailed answer with citations

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

NEVER:
- Make claims not supported by the provided papers
- Use general astronomy knowledge not in the papers
- Answer non-astronomy questions
- Provide information without citations

RESPONSE:"""
        
        return prompt
    
    def create_fallback_response(self, query: str, papers_available: bool = True) -> str:
        """Create appropriate fallback responses."""
        query_lower = query.lower()
        
        # Check if it's clearly non-astronomy
        for pattern in self.out_of_scope_patterns:
            if re.search(pattern, query_lower):
                topic = pattern.split('|')[0].strip('\\b()')
                return f"""I'm specialized in astronomy and astrophysics research, so I can't help with questions about {topic}. 

I can answer questions about:
- Black holes and stellar evolution
- Galaxy formation and structure  
- Exoplanets and planetary systems
- Cosmic phenomena and dark matter
- Observational astronomy and surveys
- Gravitational waves and cosmic rays

What would you like to know about astronomy or astrophysics?"""
        
        if not papers_available:
            return """I couldn't find any relevant research papers for your astronomy question. This might be because:

1. The topic isn't covered in our collection of 497 astronomy papers
2. The question might need different keywords
3. The specific aspect you're asking about might not be in our database

Our papers focus on:
- Black holes and stellar phenomena
- Galaxy formation and evolution
- Exoplanet discovery and characterization
- Dark matter and dark energy studies
- Observational surveys and telescope data

Could you try rephrasing your question or ask about one of these main research areas?"""
        
        return """Based on the available research papers, I don't have sufficient specific information to provide a complete answer to your question. 

The papers in our database cover various astronomy topics, but they may not contain the detailed information needed for your specific question. 

Could you try:
- Asking a more general question about the topic
- Focusing on a specific aspect mentioned in the search results
- Exploring a related astronomy topic that might be better covered

What specific aspect of astronomy or astrophysics interests you most?"""
    
    async def health_check(self) -> Dict[str, Any]:
        """Check guardrails service health."""
        return {
            "guardrails_active": True,
            "llm_classification_available": self.client is not None,
            "keyword_patterns_loaded": len(self.astronomy_keywords['core_topics']),
            "out_of_scope_patterns": len(self.out_of_scope_patterns)
        }
