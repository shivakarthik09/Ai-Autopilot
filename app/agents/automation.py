from typing import Dict, Any, List
from pydantic import BaseModel, Field
from .base import BaseAgent
import time
import logging
import json
from app.utils.openai_client import OpenAIProjectClient
from app.config import OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)

class ScriptVerification(BaseModel):
    syntax_check: bool = Field(..., description="Whether the script passed syntax validation")
    security_check: bool = Field(..., description="Whether the script passed security checks")
    lint_score: int = Field(..., description="Lint score (0-100)")
    lint_issues: List[str] = Field(..., description="List of lint issues found")
    verification_steps: List[str] = Field(..., description="Steps to verify script execution")
    expected_output: str = Field(..., description="Expected output after execution")

class ScriptResult(BaseModel):
    script: str = Field(..., description="The generated PowerShell script")
    verification: ScriptVerification = Field(..., description="Script verification results")
    dependencies: List[str] = Field(..., description="Required dependencies")
    execution_time: str = Field(..., description="Estimated execution time")
    rollback_script: str = Field(..., description="Script to rollback changes if needed")

class AutomationAgent(BaseAgent):
    def __init__(self, max_retries: int = 3):
        super().__init__("AutomationAgent")
        self.client = OpenAIProjectClient(OPENAI_API_KEY)
        self.max_retries = max_retries
        logging.info("Initialized AutomationAgent")
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        logging.info(f"[AutomationAgent] ENTER execute with task: {json.dumps(task, indent=2)}")
        retries = 0
        last_error = None
        try:
            self.validate_input(task)
            logging.info("[AutomationAgent] Input validation successful")
        except Exception as e:
            logging.error(f"[AutomationAgent] Input validation failed: {e}", exc_info=True)
            return {"error": f"Input validation failed: {e}", "status": "failed"}
        while retries < self.max_retries:
            try:
                logging.info(f"[AutomationAgent] Attempt {retries+1} to generate script")
                script = await self._generate_script(task["task"])
                logging.info(f"[AutomationAgent] Script generated: {script}")
                verification = await self._verify_script(script)
                logging.info(f"[AutomationAgent] Verification: {json.dumps(verification, indent=2)}")
                commands = []
                if script:
                    lines = script.splitlines()
                    logging.info(f"[AutomationAgent] Processing {len(lines)} lines from script")
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if line.startswith('az'):
                                commands.append(line)
                                logging.info(f"[AutomationAgent] Extracted Azure CLI command: {line}")
                            elif line.startswith('$') or line.startswith('Get-') or line.startswith('Set-') or line.startswith('New-'):
                                commands.append(line)
                                logging.info(f"[AutomationAgent] Extracted PowerShell command: {line}")
                logging.info(f"[AutomationAgent] Extracted {len(commands)} commands")
                result = {
                    "script": {
                        "language": "powershell",
                        "code": script,
                        "lint_passed": verification["syntax_check"]
                    },
                    "commands": commands,
                    "status": "success"
                }
                logging.info(f"[AutomationAgent] RETURNING result: {json.dumps(result, indent=2)}")
                return result
            except Exception as e:
                last_error = str(e)
                logging.error(f"[AutomationAgent] Error: {last_error}", exc_info=True)
                retries += 1
                if retries == self.max_retries:
                    error_result = {
                        "error": f"Failed after {retries} retries. Last error: {last_error}",
                        "status": "failed"
                    }
                    logging.error(f"[AutomationAgent] RETURNING error result: {json.dumps(error_result, indent=2)}")
                    return error_result
                logging.info(f"[AutomationAgent] Retrying (attempt {retries + 1}/{self.max_retries})")
                time.sleep(1)
        error_result = {"error": "Unexpected error in automation execution", "status": "failed"}
        logging.error(f"[AutomationAgent] RETURNING error result: {json.dumps(error_result, indent=2)}")
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
            # Replace single quotes with double quotes only for property names (not inside values)
            # This is tricky, so try JSON first
            return json.loads(content)
        except Exception:
            # Fallback: extract 'script' field with regex
            match = re.search(r'"script"\s*:\s*"([\s\S]*?)"\s*}', content)
            if match:
                script = match.group(1)
                logging.warning("[AutomationAgent] Fallback: extracted script via regex due to JSON parse error.")
                return {"script": script}
            # Try single quotes as well
            match = re.search(r'"script"\s*:\s*\'([\s\S]*?)\'\s*}', content)
            if match:
                script = match.group(1)
                logging.warning("[AutomationAgent] Fallback: extracted script via regex (single quotes) due to JSON parse error.")
                return {"script": script}
            raise ValueError("Could not extract script from LLM response (invalid JSON and no regex match).")

    async def _generate_script(self, task: str) -> str:
        logging.info(f"[AutomationAgent] ENTER _generate_script with task: {task}")
        messages = [
            {"role": "system", "content": (
                "You are an expert PowerShell and Azure CLI script writer. Generate secure, efficient scripts that follow best practices. "
                "For Azure CLI commands, generate them in a format that can be easily parsed into individual commands. "
                "Each command should be on a new line and properly formatted. "
                "For Azure CLI commands, always start each command with 'az' and ensure they are complete and executable. "
                "Do not include any explanatory text or comments in the output. "
                "IMPORTANT: Return the script as a single-line string with explicit \\n for newlines, so the JSON is always valid. Use only double quotes for all property names and string values."
            )},
            {"role": "user", "content": (
                f"Generate a script to:\n{task}\n\n"
                "Format the response as a JSON object with a 'script' field containing the script code as a single-line string with explicit \\n for newlines. "
                "For Azure CLI commands, put each command on a new line and ensure they are properly formatted. "
                "Each command should be complete and executable. "
                "Do not include any explanatory text or comments in the output."
            )}
        ]
        try:
            logging.info(f"[AutomationAgent] Sending request to OpenAI API with messages: {json.dumps(messages, indent=2)}")
            response = await self.client.create_chat_completion(
                messages=messages,
                model="gpt-3.5-turbo",
                temperature=0.7
            )
            logging.info(f"[AutomationAgent] OpenAI API raw response: {json.dumps(response, indent=2)}")
            content = response["choices"][0]["message"]["content"]
            logging.info(f"[AutomationAgent] Extracted content: {content}")
            parsed = self._parse_llm_json_response(content)
            script = parsed["script"]
            script = script.replace('\\r\\n', '\\n').replace('\\n', '\n').replace('\\r', '\n')
            logging.info(f"[AutomationAgent] Extracted script: {script}")
            return script
        except Exception as e:
            logging.error(f"[AutomationAgent] Error generating script: {str(e)}", exc_info=True)
            raise
    
    async def _verify_script(self, script: str) -> Dict[str, Any]:
        """Verify the generated script for security and best practices."""
        logging.info(f"AutomationAgent._verify_script called with script: {script}")
        messages = [
            {"role": "system", "content": "You are a PowerShell and Azure CLI script verifier. Check scripts for security issues and best practices. Return ONLY a JSON object with no additional text. Use only double quotes for all property names and string values."},
            {"role": "user", "content": f"Verify this script and return a JSON object with these exact fields:\n{script}\n\n{{\n  \"syntax_check\": boolean,\n  \"security_check\": boolean,\n  \"lint_score\": number,\n  \"lint_issues\": [string],\n  \"verification_steps\": [string],\n  \"expected_output\": string\n}}"}
        ]
        try:
            logging.info(f"AutomationAgent sending verification request to OpenAI API with messages: {json.dumps(messages, indent=2)}")
            response = await self.client.create_chat_completion(
                messages=messages,
                model="gpt-3.5-turbo",
                temperature=0.7
            )
            logging.info(f"AutomationAgent received verification response from OpenAI API: {json.dumps(response, indent=2)}")
            content = response["choices"][0]["message"]["content"]
            logging.info(f"AutomationAgent extracted verification content: {content}")
            parsed = self._parse_llm_json_response(content)
            logging.info(f"AutomationAgent parsed verification results: {json.dumps(parsed, indent=2)}")
            required_fields = ["syntax_check", "security_check", "lint_score", "lint_issues", "verification_steps", "expected_output"]
            for field in required_fields:
                if field not in parsed:
                    raise ValueError(f"Missing required field in verification: {field}")
            return parsed
        except Exception as e:
            logging.error(f"AutomationAgent error verifying script: {str(e)}", exc_info=True)
            return {
                "syntax_check": False,
                "security_check": False,
                "lint_score": 0,
                "lint_issues": [f"Verification failed: {str(e)}"],
                "verification_steps": ["Script verification failed"],
                "expected_output": "Error during script verification"
            }
    
    def validate_input(self, data: Dict[str, Any]) -> None:
        """Validate input data."""
        if not isinstance(data, dict):
            raise ValueError("Input must be a dictionary")
        
        if "task" not in data or not isinstance(data["task"], str) or not data["task"].strip():
            raise ValueError("Task must be a non-empty string") 