"""LLM client wrapper for OpenAI."""
import json
import logging
from typing import Optional
from openai import OpenAI
from utils.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper for OpenAI LLM API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize LLM client."""
        self.api_key = api_key or OPENAI_API_KEY
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("No OpenAI API key - LLM features disabled")
    
    def ask(self, question: str, resume_data: dict, job_description: str, context: str = "") -> str:
        """
        Use LLM to answer a question based on resume and job context.
        
        Args:
            question: The question to answer
            resume_data: Candidate's resume data
            job_description: Job description text
            context: Additional context/instructions
            
        Returns:
            LLM-generated answer or empty string if LLM unavailable
        """
        if not self.client:
            return ""
        
        try:
            prompt = f"""Based on the candidate's resume and the job description, provide a concise, professional answer to this application question.

Resume:
{json.dumps(resume_data, indent=2)}

Job Description:
{job_description[:2000]}

Question: {question}

{context}

Provide ONLY the answer, no explanations. Keep it brief and professional (1-3 sentences max for text fields, single word/option for multiple choice)."""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.5
            )
            answer = response.choices[0].message.content.strip()
            logger.info(f"LLM answered: {answer[:50]}...")
            return answer
            
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return ""

