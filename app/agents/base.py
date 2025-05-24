from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel
from app.utils.openai_client import OpenAIProjectClient
from app.config import OPENAI_API_KEY

class AgentResult(BaseModel):
    success: bool
    data: Dict[str, Any]
    error: str = None

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.client = OpenAIProjectClient(OPENAI_API_KEY)
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute the agent's main logic.
        Must be implemented by all agent classes.
        """
        pass
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate the input data before execution.
        Can be overridden by specific agents.
        """
        return True
    
    async def handle_error(self, error: Exception) -> AgentResult:
        """
        Handle any errors that occur during execution.
        Can be overridden by specific agents.
        """
        return AgentResult(
            success=False,
            data={},
            error=str(error)
        )
    
    async def run(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Main execution flow for the agent.
        """
        try:
            if not await self.validate_input(input_data):
                raise ValueError("Invalid input data")
            
            return await self.execute(input_data)
        except Exception as e:
            return await self.handle_error(e) 