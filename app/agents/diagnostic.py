from typing import Dict, Any, List, Union
from pydantic import BaseModel, Field
import logging
import json
from app.agents.base import BaseAgent
from app.config import OPENAI_API_KEY
import openai

logging.basicConfig(level=logging.INFO)

class Solution(BaseModel):
    description: str = Field(..., description="Detailed description of the solution")
    confidence: float = Field(..., description="Confidence level between 0 and 1")
    implementation_steps: List[str] = Field(..., description="Step-by-step implementation instructions")
    verification_steps: List[str] = Field(..., description="Steps to verify the solution worked")

class DiagnosisResult(BaseModel):
    root_cause: str = Field(..., description="Identified root cause of the issue")
    evidence: List[str] = Field(..., description="Supporting evidence for the diagnosis")
    solutions: List[Solution] = Field(..., description="Proposed solutions with confidence levels")
    complexity: str = Field(..., description="Complexity level: high, medium, or low")
    risk_level: str = Field(..., description="Risk level: high, medium, or low")
    affected_components: List[str] = Field(..., description="List of affected system components")

class DiagnosticAgent(BaseAgent):
    def __init__(self):
        super().__init__("DiagnosticAgent")
        self.client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        logging.info("Initialized DiagnosticAgent")
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute diagnostic analysis."""
        logging.info(f"DiagnosticAgent.execute called with task: {json.dumps(task, indent=2)}")
        try:
            # Validate input
            if not isinstance(task, dict) or "task" not in task:
                raise ValueError("Invalid task format")
            logging.info("DiagnosticAgent input validation successful")
            
            # Generate diagnosis using OpenAI
            messages = [
                {"role": "system", "content": (
                    "You are an expert IT diagnostician. Analyze the given task and provide a diagnosis "
                    "in the following JSON format:\n"
                    "{\n"
                    "  \"root_cause\": \"Brief description of the root cause\",\n"
                    "  \"evidence\": [\"List of evidence points\"],\n"
                    "  \"solutions\": [\n"
                    "    {\n"
                    "      \"title\": \"Solution title\",\n"
                    "      \"confidence\": \"High/Medium/Low\"\n"
                    "    }\n"
                    "  ]\n"
                    "}\n"
                    "Respond ONLY with the JSON object, no other text."
                )},
                {"role": "user", "content": f"Analyze this task: {task['task']}"}
            ]
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            logging.info(f"OpenAI API raw response: {response}")
            
            # Try to parse the response as JSON
            try:
                # First try direct JSON parsing
                diagnosis = json.loads(result_text)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from markdown code blocks
                import re
                json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', result_text)
                if json_match:
                    try:
                        diagnosis = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        logging.warning("[DiagnosticAgent] Failed to parse JSON from markdown code block")
                        diagnosis = {
                            "root_cause": "Could not parse diagnosis",
                            "evidence": [],
                            "solutions": []
                        }
                else:
                    logging.warning("[DiagnosticAgent] No JSON found in response")
                    diagnosis = {
                        "root_cause": "Could not parse diagnosis",
                        "evidence": [],
                        "solutions": []
                    }
            
            logging.info(f"DiagnosticAgent generated diagnosis: {json.dumps(diagnosis, indent=2)}")
            
            return {
                "diagnosis": diagnosis,
                "status": "success"
            }
        except Exception as e:
            logging.error(f"Error in DiagnosticAgent.execute: {e}", exc_info=True)
            return {
                "diagnosis": {
                    "root_cause": f"Error in diagnosis: {str(e)}",
                    "evidence": [],
                    "solutions": []
                },
                "status": "failed",
                "error": str(e)
            }

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
            # Fallback: extract the whole object as a string (between first { and last })
            match = re.search(r'(\{[\s\S]+\})', content)
            if match:
                obj_str = match.group(1)
                logging.warning("[DiagnosticAgent] Fallback: extracted diagnosis via regex due to JSON parse error.")
                try:
                    # Try to fix single quotes
                    obj_str = obj_str.replace("'", '"')
                    return json.loads(obj_str)
                except Exception:
                    return {"root_cause": "Could not parse diagnosis", "evidence": [], "solutions": []}
            raise ValueError("Could not extract diagnosis from LLM response (invalid JSON and no regex match).")

    async def _generate_diagnosis(self, task: str) -> Dict[str, Any]:
        """Generate a diagnosis for the given task."""
        messages = [
            {"role": "system", "content": (
                "You are an expert IT diagnostician. Analyze issues and provide detailed diagnoses "
                "with evidence-based solutions. Format your response as a JSON object. Use only double quotes for all property names and string values."
            )},
            {"role": "user", "content": (
                f"Diagnose this issue and provide solutions:\n{task}\n\n"
                "Format the response as a JSON object with these fields:\n"
                "- root_cause: string\n"
                "- evidence: array of strings\n"
                "- solutions: array of objects with 'title' and 'confidence' fields"
            )}
        ]
        try:
            response = await self.client.create_chat_completion(
                messages=messages,
                model="gpt-3.5-turbo",
                temperature=0.7
            )
            content = response["choices"][0]["message"]["content"]
            diagnosis = self._parse_llm_json_response(content)
            return diagnosis
        except Exception as e:
            logging.error(f"DiagnosticAgent error generating diagnosis: {str(e)}", exc_info=True)
            raise

    def validate_input(self, data: Dict[str, Any]) -> None:
        """Validate input data."""
        if not isinstance(data, dict):
            raise ValueError("Input must be a dictionary")
        
        if "task" not in data or not isinstance(data["task"], str) or not data["task"].strip():
            raise ValueError("Task must be a non-empty string") 