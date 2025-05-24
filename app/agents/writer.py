from typing import Dict, Any, List
from pydantic import BaseModel, Field
from .base import BaseAgent
import logging
import json
from app.utils.openai_client import OpenAIProjectClient
from app.config import OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)

class ActionItem(BaseModel):
    description: str = Field(..., description="Description of the action item")
    assignee: str = Field(..., description="Person or team responsible")
    due_date: str = Field(..., description="Due date for the action item")
    priority: str = Field(..., description="Priority level: high, medium, or low")

class EmailDraft(BaseModel):
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Formatted email body")
    key_points: List[str] = Field(..., description="Key points to highlight")
    action_items: List[ActionItem] = Field(..., description="Action items with assignments")
    attachments: List[str] = Field(..., description="List of required attachments")
    cc_recipients: List[str] = Field(..., description="List of CC recipients")
    bcc_recipients: List[str] = Field(..., description="List of BCC recipients")
    follow_up_date: str = Field(..., description="Date for follow-up if needed")

class WriterAgent(BaseAgent):
    def __init__(self):
        super().__init__("WriterAgent")
        self.client = OpenAIProjectClient(OPENAI_API_KEY)
        logging.info("Initialized WriterAgent")
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute writing task."""
        logging.info(f"WriterAgent.execute called with task: {json.dumps(task, indent=2)}")
        try:
            # Validate input (await if coroutine)
            validate_result = self.validate_input(task)
            if hasattr(validate_result, '__await__'):
                await validate_result
            logging.info("WriterAgent input validation successful")
            
            # Generate email draft
            email_draft = await self._generate_email(task["task"])
            logging.info(f"WriterAgent generated email draft: {email_draft}")
            
            result = {
                "email_draft": email_draft,
                "status": "success"
            }
            logging.info(f"WriterAgent returning result: {json.dumps(result, indent=2)}")
            return result
            
        except Exception as e:
            error_result = {
                "error": str(e),
                "status": "failed"
            }
            logging.error(f"WriterAgent error: {str(e)}", exc_info=True)
            logging.error(f"WriterAgent returning error result: {json.dumps(error_result, indent=2)}")
            return error_result
    
    def _parse_llm_json_response(self, content: str) -> dict:
        import re
        content = content.strip()
        if not content.startswith('{'):
            start_idx = content.find('{')
            if start_idx != -1:
                content = content[start_idx:]
        # Try to parse as JSON first
        try:
            return json.loads(content)
        except Exception:
            # Fallback: extract 'email' field with regex
            match = re.search(r'"email"\s*:\s*"([\s\S]*?)"\s*}', content)
            if match:
                email = match.group(1)
                logging.warning("[WriterAgent] Fallback: extracted email via regex due to JSON parse error.")
                return {"email": email}
            # Try single quotes as well
            match = re.search(r'"email"\s*:\s*\'([\s\S]*?)\'\s*}', content)
            if match:
                email = match.group(1)
                logging.warning("[WriterAgent] Fallback: extracted email via regex (single quotes) due to JSON parse error.")
                return {"email": email}
            raise ValueError("Could not extract email from LLM response (invalid JSON and no regex match).")

    async def _generate_email(self, task: str) -> str:
        """Generate an email draft using the LLM."""
        logging.info(f"WriterAgent._generate_email called with task: {task}")
        messages = [
            {"role": "system", "content": "You are an expert technical writer. Generate clear, professional email drafts. Use only double quotes for all property names and string values."},
            {"role": "user", "content": f"Generate an email draft for:\n{task}\n\nFormat the response as a JSON object with an 'email' field containing the draft."}
        ]
        try:
            logging.info(f"WriterAgent sending request to OpenAI API with messages: {json.dumps(messages, indent=2)}")
            response = await self.client.create_chat_completion(
                messages=messages,
                model="gpt-3.5-turbo",
                temperature=0.7
            )
            # Log the raw response
            logging.info(f"WriterAgent received response from OpenAI API: {json.dumps(response, indent=2)}")
            # Extract and parse the response
            content = response["choices"][0]["message"]["content"]
            logging.info(f"WriterAgent extracted content from response: {content}")
            parsed = self._parse_llm_json_response(content)
            email = parsed["email"]
            logging.info(f"WriterAgent parsed email draft: {email}")
            return email
        except Exception as e:
            logging.error(f"WriterAgent error generating email: {str(e)}", exc_info=True)
            raise

    def _format_diagnosis(self, diagnosis: Dict[str, Any]) -> str:
        """Format diagnosis information for the email context."""
        if not diagnosis:
            return "No diagnosis information available."
            
        formatted = []
        
        if "root_cause" in diagnosis:
            formatted.append(f"Root Cause: {diagnosis['root_cause']}")
            
        if "evidence" in diagnosis:
            formatted.append("\nEvidence:")
            for evidence in diagnosis["evidence"]:
                formatted.append(f"- {evidence}")
                
        if "solutions" in diagnosis:
            formatted.append("\nProposed Solutions:")
            for solution in diagnosis["solutions"]:
                formatted.append(f"- {solution['title']} (Confidence: {solution['confidence']})")
                
        return "\n".join(formatted)

    def _format_script(self, script: Dict[str, Any]) -> str:
        """Format script information for the email context."""
        if not script:
            return "No script information available."
            
        formatted = []
        
        if "code" in script:
            formatted.append("Script Overview:")
            formatted.append(script["code"][:200] + "...")  # First 200 characters
            
        if "lint_passed" in script:
            formatted.append(f"\nScript Validation: {'Passed' if script['lint_passed'] else 'Failed'}")
            
        return "\n".join(formatted)

    def validate_input(self, data: Dict[str, Any]) -> None:
        """Validate input data."""
        if not isinstance(data, dict):
            raise ValueError("Input must be a dictionary")
        
        if "task" not in data or not isinstance(data["task"], str) or not data["task"].strip():
            raise ValueError("Task must be a non-empty string")
            
        # Validate optional fields if present
        if "diagnosis" in data and not isinstance(data["diagnosis"], dict):
            raise ValueError("Diagnosis must be a dictionary")
            
        if "script" in data and not isinstance(data["script"], dict):
            raise ValueError("Script must be a dictionary")
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate the input data."""
        return (
            "task" in input_data and 
            isinstance(input_data["task"], str) and
            len(input_data["task"]) > 0
        ) 