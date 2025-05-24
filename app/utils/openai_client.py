from typing import Dict, Any, List
from openai import AsyncOpenAI
from app.config import OPENAI_API_KEY
import logging

class OpenAIProjectClient:
    def __init__(self, api_key: str = OPENAI_API_KEY):
        self.client = AsyncOpenAI(api_key=api_key)

    async def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """Create a chat completion using the OpenAI API."""
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            logging.info(f"OpenAI API raw response: {response}")
            return response.model_dump()
        except Exception as e:
            logging.error(f"Error creating chat completion: {str(e)}")
            raise Exception(f"Error creating chat completion: {str(e)}")

    async def count_tokens(self, text: str) -> int:
        """Count tokens in a text string."""
        try:
            response = await self.client.tokens.count(
                text=text
            )
            return response.usage.total_tokens
        except Exception as e:
            # If tokenizer endpoint fails, estimate tokens (rough approximation)
            return len(text.split()) * 1.3 