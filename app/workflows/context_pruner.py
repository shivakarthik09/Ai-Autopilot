from typing import Dict, Any, List
import openai
from app.config import OPENAI_API_KEY

class ContextPruner:
    """MCP (Model Context Pruning) for efficient context management."""
    
    def __init__(self):
        self.model = "gpt-3.5-turbo"
        self.client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    async def prune_context(self, context: Dict[str, Any], max_tokens: int = 4000) -> Dict[str, Any]:
        """Prune the context to fit within token limits while preserving essential information."""
        # Convert context to string for analysis
        context_str = self._dict_to_string(context)
        
        # Get token count
        token_count = await self._count_tokens(context_str)
        
        if token_count <= max_tokens:
            return context
        
        # Prune context if it exceeds token limit
        return await self._prune_context(context, max_tokens)
    
    async def _count_tokens(self, text: str) -> int:
        """Count the number of tokens in the text."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": text}],
            max_tokens=1
        )
        return response.usage.total_tokens
    
    def _dict_to_string(self, data: Dict[str, Any]) -> str:
        """Convert dictionary to string representation."""
        if isinstance(data, dict):
            return "\n".join(f"{k}: {self._dict_to_string(v)}" for k, v in data.items())
        elif isinstance(data, list):
            return "\n".join(self._dict_to_string(item) for item in data)
        else:
            return str(data)
    
    async def _prune_context(self, context: Dict[str, Any], max_tokens: int) -> Dict[str, Any]:
        """Prune the context to fit within token limits."""
        # Create a prompt for the LLM to analyze importance
        prompt = f"""Analyze the following context and identify the most important information to preserve:

Context:
{self._dict_to_string(context)}

Please identify which parts are essential and which can be pruned to fit within {max_tokens} tokens.
Focus on preserving:
1. Critical diagnostic information
2. Key action items
3. Important configuration details
4. Essential error messages
5. Core functionality descriptions

Return a JSON object with the same structure but with pruned content."""

        # Get LLM's analysis
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a context pruning expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )

        try:
            # Parse the pruned context
            pruned_context = eval(response.choices[0].message.content)
            
            # Verify token count
            pruned_str = self._dict_to_string(pruned_context)
            pruned_tokens = await self._count_tokens(pruned_str)
            
            if pruned_tokens > max_tokens:
                # If still too large, recursively prune
                return await self._prune_context(pruned_context, max_tokens)
            
            return pruned_context
            
        except Exception as e:
            # If parsing fails, fall back to basic pruning
            return self._basic_prune(context)
    
    def _basic_prune(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Basic pruning strategy when LLM pruning fails."""
        pruned = {}
        
        # Preserve essential fields
        essential_fields = [
            "task_id", "status", "root_cause", "solutions",
            "script", "verification", "action_items"
        ]
        
        for field in essential_fields:
            if field in context:
                if isinstance(context[field], dict):
                    pruned[field] = self._basic_prune(context[field])
                elif isinstance(context[field], list):
                    pruned[field] = context[field][:3]  # Keep only first 3 items
                else:
                    pruned[field] = context[field]
        
        return pruned
    
    async def optimize_for_agent(self, context: Dict[str, Any], agent_type: str) -> Dict[str, Any]:
        """Optimize context for specific agent type."""
        # Create agent-specific prompt
        prompt = f"""Optimize the following context for a {agent_type}:

Context:
{self._dict_to_string(context)}

Please identify and preserve only the information relevant to the {agent_type}'s task.
Remove any irrelevant details while maintaining the essential context."""

        # Get LLM's optimization
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a context optimization expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )

        try:
            # Parse the optimized context
            optimized_context = eval(response.choices[0].message.content)
            return optimized_context
            
        except Exception as e:
            # If parsing fails, return original context
            return context 