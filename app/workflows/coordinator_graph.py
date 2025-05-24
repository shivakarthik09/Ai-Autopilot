from typing import Dict, Any, List, TypedDict, Annotated, Tuple
import operator
from langgraph.graph import StateGraph, END, Graph
from dotenv import load_dotenv
import os
import openai
from app.config import OPENAI_API_KEY
import json
from app.agents.diagnostic import DiagnosticAgent
from app.agents.automation import AutomationAgent
from app.agents.writer import WriterAgent
from app.workflows.task_router import TaskRouter
import time
import logging

load_dotenv()
openai.api_key = OPENAI_API_KEY

# Initialize agents
diagnostic_agent = DiagnosticAgent()
automation_agent = AutomationAgent()
writer_agent = WriterAgent()

# Define the state schema
class WorkflowState(TypedDict):
    task: str
    status: str
    analysis: Dict[str, Any]
    diagnosis: Dict[str, Any]
    script: Dict[str, Any]
    email_draft: str
    errors: List[str]
    results: Dict[str, Any]
    commands: List[str]

def analyze_request_prompt(task: str) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": (
            "You are an expert IT workflow planner. Analyze IT requests and determine which specialized agents are needed. "
            "For any task involving Azure CLI commands, scripts, or automation, ALWAYS include the 'automation' agent. "
            "For any task involving communication or documentation, ALWAYS include the 'writer' agent. "
            "For any task involving analysis or diagnosis, ALWAYS include the 'diagnostic' agent. "
            "Respond ONLY with a valid JSON object as described."
        )},
        {"role": "user", "content": f"""Analyze the following IT request and determine which specialized agents are needed:\nRequest: {task}\n\nReturn a JSON object with:\n{{\n  \"required_agents\": [\"diagnostic\", \"automation\", \"writer\"],\n  \"steps\": [\n    {{\n      \"agent\": \"agent_name\",\n      \"action\": \"action_description\",\n      \"priority\": 1\n    }}\n  ],\n  \"summary\": \"Brief description of the plan\"\n}}\n\nGuidelines:\n1. If the task mentions Azure CLI, scripts, or automation, ALWAYS include 'automation'\n2. If the task involves communication or documentation, ALWAYS include 'writer'\n3. If the task requires analysis or diagnosis, ALWAYS include 'diagnostic'\n4. Include ALL agents that could be relevant to the task\n5. Only exclude agents if they are completely irrelevant to the task"""}
    ]

async def analyze_request(state: WorkflowState) -> WorkflowState:
    """Analyze the request to determine required agents and steps."""
    try:
        task = state["task"]
        messages = analyze_request_prompt(task)
        client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        result_text = response.choices[0].message.content.strip()
        analysis = json.loads(result_text)
        state["analysis"] = analysis
        return state
    except Exception as e:
        state["errors"] = [f"Error in analyze_request: {str(e)}"]
        return state

async def execute_diagnostic(state: WorkflowState) -> WorkflowState:
    """Execute the diagnostic agent if required."""
    try:
        if "diagnostic" not in state["analysis"]["required_agents"]:
            return state
        result = await diagnostic_agent.execute({"task": state["task"]})
        state["diagnosis"] = result.get("diagnosis")
        return state
    except Exception as e:
        state["errors"] = state.get("errors", []) + [f"Error in execute_diagnostic: {str(e)}"]
        return state

async def execute_automation(state: WorkflowState) -> WorkflowState:
    """Execute the automation agent if required."""
    logging.info(f"[CoordinatorGraph] ENTER execute_automation with state: {json.dumps(state, indent=2)}")
    try:
        if "automation" not in state["analysis"]["required_agents"]:
            return state
        result = await automation_agent.execute({"task": state["task"]})
        logging.info(f"[CoordinatorGraph] Automation agent result: {json.dumps(result, indent=2)}")
        state["script"] = result.get("script")
        # If the script is an Azure CLI or similar, extract commands
        if result.get("commands"):
            state["commands"] = result["commands"]
        elif state["script"] and state["script"].get("code") and state["script"].get("language", "").lower() in ["azure cli", "bash", "powershell"]:
            # Try to extract commands from code if possible (for CLI tasks)
            state["commands"] = [line.strip() for line in state["script"]["code"].splitlines() if line.strip()]
        logging.info(f"[CoordinatorGraph] State after automation: {json.dumps(state, indent=2)}")
        return state
    except Exception as e:
        logging.error(f"[CoordinatorGraph] Error in execute_automation: {e}", exc_info=True)
        state["errors"] = state.get("errors", []) + [f"Error in execute_automation: {str(e)}"]
        return state

async def execute_writer(state: WorkflowState) -> WorkflowState:
    """Execute the writer agent if required."""
    try:
        if "writer" not in state["analysis"]["required_agents"]:
            return state
        # Pass diagnosis and script as context
        result = await writer_agent.execute({
            "task": state["task"],
            "diagnosis": state.get("diagnosis"),
            "script": state.get("script")
        })
        state["email_draft"] = result.get("email_draft")
        return state
    except Exception as e:
        state["errors"] = state.get("errors", []) + [f"Error in execute_writer: {str(e)}"]
        return state

async def merge_results(state: WorkflowState) -> WorkflowState:
    """Merge all agent results into a final response."""
    logging.info(f"[CoordinatorGraph] ENTER merge_results with state: {json.dumps(state, indent=2)}")
    try:
        commands = state.get("commands", [])
        script = state.get("script", {}) or {}
        if not commands and script.get("code"):
            script_lines = script["code"].splitlines()
            commands = [line.strip() for line in script_lines if line.strip() and not line.strip().startswith('#')]
            logging.info(f"[CoordinatorGraph] Extracted commands from script: {json.dumps(commands, indent=2)}")
        
        # Ensure email_draft is a string
        email_draft = state.get("email_draft")
        if isinstance(email_draft, dict):
            email_draft = json.dumps(email_draft)
        
        results = {
            "diagnosis": state.get("diagnosis"),
            "script": script,
            "email_draft": email_draft,
            "commands": commands
        }
        logging.info(f"[CoordinatorGraph] Merged results: {json.dumps(results, indent=2)}")
        state["results"] = results
        required_agents = state["analysis"].get("required_agents", [])
        logging.info(f"[CoordinatorGraph] merge_results: diagnosis value: {json.dumps(state.get('diagnosis'), indent=2)}")
        completed_agents = []
        failed_agents = []
        # Filter out retry-related errors
        non_retry_errors = [
            e for e in state.get("errors", [])
            if not ("First attempt failed" in e or "automation" in e and "failed" in e)
        ]
        # Check each required agent's completion status
        if "diagnostic" in required_agents:
            diagnosis = state.get("diagnosis")
            if diagnosis is not None:
                completed_agents.append("diagnostic")
            elif non_retry_errors and any("Error in execute_diagnostic" in error for error in non_retry_errors):
                failed_agents.append("diagnostic")
        if "automation" in required_agents:
            if script is not None:
                completed_agents.append("automation")
            elif non_retry_errors and any("Error in execute_automation" in error for error in non_retry_errors):
                failed_agents.append("automation")
        if "writer" in required_agents:
            if email_draft is not None:
                completed_agents.append("writer")
            elif non_retry_errors and any("Error in execute_writer" in error for error in non_retry_errors):
                failed_agents.append("writer")
        logging.info(f"[CoordinatorGraph] required_agents: {required_agents}, completed_agents: {completed_agents}, failed_agents: {failed_agents}")
        # Set final status based on agent completion
        if len(completed_agents) == len(required_agents):
            state["status"] = "completed"
        elif failed_agents:
            state["status"] = "failed"
        else:
            state["status"] = "in_progress"
        logging.info(f"[CoordinatorGraph] merge_results returning status: {state['status']}")
        return state
    except Exception as e:
        logging.error(f"[CoordinatorGraph] Error in merge_results: {e}", exc_info=True)
        state["errors"] = state.get("errors", []) + [f"Error in merge_results: {str(e)}"]
        state["status"] = "failed"
        return state

def create_coordinator_graph() -> StateGraph:
    """Create the coordinator workflow graph."""
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("analyze_request", analyze_request)
    workflow.add_node("execute_diagnostic", execute_diagnostic)
    workflow.add_node("execute_automation", execute_automation)
    workflow.add_node("execute_writer", execute_writer)
    workflow.add_node("merge_results", merge_results)
    
    # Add edges with conditional routing
    workflow.add_edge("analyze_request", "execute_diagnostic")
    # After diagnostic, go to automation if required, else merge
    workflow.add_edge("execute_diagnostic", "execute_automation", condition=lambda state: "automation" in state["analysis"].get("required_agents", []))
    workflow.add_edge("execute_diagnostic", "merge_results", condition=lambda state: "automation" not in state["analysis"].get("required_agents", []))
    # After automation, go to writer if required, else merge
    workflow.add_edge("execute_automation", "execute_writer", condition=lambda state: "writer" in state["analysis"].get("required_agents", []))
    workflow.add_edge("execute_automation", "merge_results", condition=lambda state: "writer" not in state["analysis"].get("required_agents", []))
    # After writer, always go to merge
    workflow.add_edge("execute_writer", "merge_results")
    workflow.add_edge("merge_results", END)
    
    # Set entry point
    workflow.set_entry_point("analyze_request")
    
    return workflow

class CoordinatorGraph:
    def __init__(self):
        self.diagnostic_agent = DiagnosticAgent()
        self.automation_agent = AutomationAgent()
        self.writer_agent = WriterAgent()
        self.task_router = TaskRouter()
        
    def create_graph(self) -> Graph:
        """Create the main workflow graph."""
        # Initialize the graph
        workflow = StateGraph(WorkflowState)
        
        # Define the nodes
        workflow.add_node("analyze_task", self._analyze_task)
        workflow.add_node("execute_diagnostic", self._execute_diagnostic)
        workflow.add_node("execute_automation", self._execute_automation)
        workflow.add_node("execute_writer", self._execute_writer)
        workflow.add_node("merge_results", merge_results)  # Use the global merge_results function
        
        # Define the edges
        workflow.add_edge("analyze_task", "execute_diagnostic")
        workflow.add_edge("execute_diagnostic", "execute_automation")
        workflow.add_edge("execute_automation", "execute_writer")
        workflow.add_edge("execute_writer", "merge_results")
        workflow.add_edge("merge_results", END)
        
        # Set the entry point
        workflow.set_entry_point("analyze_task")
        
        return workflow.compile()
    
    async def _analyze_task(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the task and determine required agents."""
        task = state["task"]
        analysis = self.task_router.analyze_task(task)
        
        return {
            **state,
            "analysis": analysis,
            "required_agents": analysis["required_agents"],
            "requires_approval": analysis["requires_approval"]
        }
    
    async def _execute_diagnostic(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logging.info(f"[CoordinatorGraph] ENTER _execute_diagnostic with state: {json.dumps(state, indent=2)}")
        if "diagnostic" in state.get("analysis", {}).get("required_agents", []):
            try:
                result = await self.diagnostic_agent.execute({"task": state["task"]})
                logging.info(f"[CoordinatorGraph] Diagnostic agent result: {json.dumps(result, indent=2)}")
                return {**state, "diagnosis": result.get("diagnosis")}
            except Exception as e:
                logging.error(f"[CoordinatorGraph] Error in _execute_diagnostic: {e}", exc_info=True)
                state["errors"] = state.get("errors", []) + [f"Error in execute_diagnostic: {str(e)}"]
                return state
        logging.info(f"[CoordinatorGraph] SKIP _execute_diagnostic (not required)")
        return state
    
    async def _execute_automation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logging.info(f"[CoordinatorGraph] ENTER _execute_automation with state: {json.dumps(state, indent=2)}")
        if "automation" in state.get("analysis", {}).get("required_agents", []):
            result = await self.automation_agent.execute({"task": state["task"]})
            # Always update state with the latest result
            new_state = {**state}
            if result.get("script") is not None:
                new_state["script"] = result.get("script")
            if result.get("commands") is not None:
                new_state["commands"] = result.get("commands")
            if result.get("status") == "failed":
                new_state["errors"] = new_state.get("errors", []) + [result.get("error", "Automation agent failed")]
            else:
                # On success, remove any previous automation-related errors
                new_state["errors"] = [
                    e for e in new_state.get("errors", [])
                    if not ("automation" in e or "First attempt failed" in e)
                ]
            logging.info(f"[CoordinatorGraph] State after automation: {json.dumps(new_state, indent=2)}")
            return new_state
        logging.info(f"[CoordinatorGraph] SKIP _execute_automation (not required)")
        return state
    
    async def _execute_writer(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logging.info(f"[CoordinatorGraph] ENTER _execute_writer with state: {json.dumps(state, indent=2)}")
        if "writer" in state.get("analysis", {}).get("required_agents", []):
            try:
                result = await self.writer_agent.execute({
                    "task": state["task"],
                    "diagnosis": state.get("diagnosis"),
                    "script": state.get("script")
                })
                logging.info(f"[CoordinatorGraph] Writer agent result: {json.dumps(result, indent=2)}")
                return {**state, "email_draft": result.get("email_draft")}
            except Exception as e:
                logging.error(f"[CoordinatorGraph] Error in _execute_writer: {e}", exc_info=True)
                state["errors"] = state.get("errors", []) + [f"Error in execute_writer: {str(e)}"]
                return state
        logging.info(f"[CoordinatorGraph] SKIP _execute_writer (not required)")
        return state
    
    async def execute(self, task: str, task_id: str) -> Dict[str, Any]:
        """Execute the workflow for a given task."""
        # Create initial state
        initial_state = {
            "task": task,
            "status": "in_progress",
            "analysis": {},
            "diagnosis": None,
            "script": None,
            "email_draft": None,
            "errors": [],
            "results": {},
            "commands": []
        }
        
        # Create and run the graph
        graph = self.create_graph()
        final_state = await graph.ainvoke(initial_state)
        
        return final_state 