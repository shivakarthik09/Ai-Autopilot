from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.utils.openai_client import OpenAIProjectClient
from dotenv import load_dotenv
import os
from app.workflows.coordinator_graph import create_coordinator_graph, WorkflowState, CoordinatorGraph
from app.agents.diagnostic import DiagnosticAgent
from app.agents.automation import AutomationAgent
from app.agents.writer import WriterAgent
from app.config import OPENAI_API_KEY
import json
from datetime import datetime
import uuid
from fastapi import HTTPException
from app.workflows.task_router import TaskRouter
from app.workflows.dspy_router import DSPyRouter
from app.workflows.context_pruner import ContextPruner
from app.workflows.diagnostic_graph import DiagnosticGraph
import time
import logging

load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Log OpenAI API key status
if OPENAI_API_KEY:
    logging.info(f"Loaded OPENAI_API_KEY: {OPENAI_API_KEY[:4]}...{OPENAI_API_KEY[-4:]}")
else:
    logging.error("OPENAI_API_KEY is not set!")

# In-memory task storage (replace with proper database in production)
class TaskStorage:
    _instance = None
    _tasks = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskStorage, cls).__new__(cls)
        return cls._instance
    
    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(task_id)
    
    def set(self, task_id: str, task_data: Dict[str, Any]) -> None:
        self._tasks[task_id] = task_data
    
    def all(self):
        return list(self._tasks.values())
    
    def clear(self):
        self._tasks.clear()

# Create a single instance of TaskStorage
task_storage = TaskStorage()

class TaskResponse(BaseModel):
    """Standardized task response model."""
    task_id: str
    status: str
    duration_seconds: float
    error: Optional[str] = None
    diagnosis: Optional[Dict[str, Any]] = None
    script: Optional[Dict[str, Any]] = None
    email_draft: Optional[str] = None
    commands: List[str] = Field(default_factory=list)
    plan: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

class Coordinator:
    def __init__(self):
        self.coordinator_graph = CoordinatorGraph()
        self.dspy_router = DSPyRouter()
        self.context_pruner = ContextPruner()
        self.diagnostic_graph = DiagnosticGraph()
        self.tasks = {}
        self.client = OpenAIProjectClient(api_key=OPENAI_API_KEY)
    
    async def execute_task(self, task: str, require_approval: bool = False) -> TaskResponse:
        """Execute a task with optional approval workflow."""
        start_time = time.time()
        task_id = str(uuid.uuid4())
        
        try:
            logging.info(f"Executing task: {task} (require_approval={require_approval})")
            # Analyze task using the same TaskRouter as the coordinator graph for consistency
            analysis = TaskRouter().analyze_task(task)
            logging.info(f"Agent analysis for approval plan: {json.dumps(analysis, indent=2)}")
            
            # Create task record
            task_record = {
                "task_id": task_id,
                "task": task,
                "status": "waiting_approval" if require_approval or analysis["requires_approval"] else "in_progress",
                "type": analysis["task_type"],
                "required_agents": analysis["required_agents"],
                "complexity": analysis["complexity"],
                "start_time": start_time,
                "result": {}  # Initialize empty result
            }
            
            # Store task record
            self.tasks[task_id] = task_record
            
            # If approval required, return plan for approval
            if task_record["status"] == "waiting_approval":
                return TaskResponse(
                    task_id=task_id,
                    status="waiting_approval",
                    duration_seconds=time.time() - start_time,
                    plan={
                        "steps": [f"Execute {agent}" for agent in analysis["required_agents"]],
                        "summary": f"Will execute {len(analysis['required_agents'])} agents for {analysis['task_type']} task"
                    }
                )
            
            # Execute task immediately if no approval required
            return await self._execute_approved_task(task_id)
            
        except Exception as e:
            logging.error(f"Error in execute_task: {e}", exc_info=True)
            return TaskResponse(
                task_id=task_id,
                status="failed",
                duration_seconds=time.time() - start_time,
                error=str(e)
            )
    
    async def _execute_approved_task(self, task_id: str) -> TaskResponse:
        """Execute an approved task."""
        task_record = self.tasks[task_id]
        start_time = task_record["start_time"]
        
        try:
            logging.info(f"Executing approved task: {task_id}")
            
            # Execute using coordinator graph
            final_state = await self.coordinator_graph.execute(
                task=task_record["task"],
                task_id=task_id
            )
            
            # Use the final state's status and results
            processed_result = final_state.get("results", {})
            status = final_state.get("status", "in_progress")
            required_agents = final_state.get("analysis", {}).get("required_agents", [])
            errors = final_state.get("errors", [])
            
            # Filter out retry-related errors
            non_retry_errors = [
                e for e in errors
                if not ("First attempt failed" in e or "automation" in e and "failed" in e)
            ]
            
            logging.info(f"[Coordinator] Final status: {status}, required_agents: {required_agents}")
            logging.info(f"[Coordinator] Errors: {errors}")
            logging.info(f"[Coordinator] Non-retry errors: {non_retry_errors}")
            
            # Only mark as failed if there are non-retry errors
            if status == "failed" and not non_retry_errors:
                status = "in_progress"
            
            # Update task record with status
            task_record.update({
                "status": status,
                "result": processed_result,
                "end_time": time.time(),
                "duration_seconds": time.time() - start_time,
                "errors": errors
            })
            
            # Return standardized response
            return TaskResponse(
                task_id=task_id,
                status=status,
                duration_seconds=time.time() - start_time,
                diagnosis=processed_result.get("diagnosis"),
                script=processed_result.get("script"),
                email_draft=processed_result.get("email_draft"),
                commands=processed_result.get("commands", []),
                plan=task_record.get("plan"),
                errors=errors if errors else None
            )
        except Exception as e:
            logging.error(f"Error in _execute_approved_task: {e}", exc_info=True)
            # Update task record with error
            task_record.update({
                "status": "failed",
                "error": str(e),
                "end_time": time.time(),
                "duration_seconds": time.time() - start_time
            })
            return TaskResponse(
                task_id=task_id,
                status="failed",
                duration_seconds=time.time() - start_time,
                error=str(e)
            )
    
    async def approve_task(self, task_id: str) -> TaskResponse:
        """Approve a pending task."""
        if task_id not in self.tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            
        task_record = self.tasks[task_id]
        
        if task_record["status"] != "waiting_approval":
            raise HTTPException(status_code=400, detail=f"Task {task_id} is not pending approval")
        
        # Execute the approved task
        return await self._execute_approved_task(task_id)
    
    async def reject_task(self, task_id: str) -> TaskResponse:
        """Reject a pending task."""
        if task_id not in self.tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            
        task_record = self.tasks[task_id]
        
        if task_record["status"] != "waiting_approval":
            raise HTTPException(status_code=400, detail=f"Task {task_id} is not pending approval")
        
        # Update task record
        task_record.update({
            "status": "rejected",
            "end_time": time.time(),
            "duration_seconds": time.time() - task_record["start_time"]
        })
        
        return TaskResponse(
            task_id=task_id,
            status="rejected",
            duration_seconds=time.time() - task_record["start_time"]
        )
    
    async def get_task(self, task_id: str) -> TaskResponse:
        """Get task status and results."""
        if task_id not in self.tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            
        task_record = self.tasks[task_id]
        result = task_record.get("result", {})
        
        return TaskResponse(
            task_id=task_id,
            status=task_record["status"],
            duration_seconds=time.time() - task_record["start_time"],
            error=task_record.get("error"),
            diagnosis=result.get("diagnosis"),
            script=result.get("script"),
            email_draft=result.get("email_draft"),
            commands=result.get("commands", []),
            plan=task_record.get("plan")
        )
    
    async def list_tasks(self) -> List[TaskResponse]:
        """List all tasks."""
        return [
            TaskResponse(
                task_id=task_id,
                status=record["status"],
                duration_seconds=time.time() - record["start_time"],
                error=record.get("error"),
                diagnosis=record.get("result", {}).get("diagnosis"),
                script=record.get("result", {}).get("script"),
                email_draft=record.get("result", {}).get("email_draft"),
                commands=record.get("result", {}).get("commands"),
                plan=record.get("plan")
            )
            for task_id, record in self.tasks.items()
        ]

class CoordinatorAgent:
    def __init__(self):
        self.graph = create_coordinator_graph().compile()  # Compile the graph
        self.diagnostic_agent = DiagnosticAgent()
        self.automation_agent = AutomationAgent()
        self.writer_agent = WriterAgent()
        self.storage = task_storage
    
    async def process_request(self, request: str, require_approval: bool = True) -> Dict[str, Any]:
        """Process a new request and create a task."""
        try:
            # Create task ID
            task_id = str(uuid.uuid4())
            
            # Create initial workflow state
            state = {
                "task": request,
                "status": "pending",
                "analysis": None,
                "diagnosis": None,
                "script": None,
                "email_draft": None,
                "errors": [],
                "results": {}
            }
            
            if require_approval:
                # Create plan for approval
                plan = await self._create_plan(request)
                if "error" in plan:
                    return {
                        "status": "failed",
                        "errors": [plan["error"]]
                    }
                state["analysis"] = plan
                state["status"] = "pending_approval"
                
                # Store task information
                self.storage.set(task_id, {
                    "id": task_id,
                    "status": "pending_approval",
                    "request": request,
                    "created_at": datetime.utcnow(),
                    "plan": plan,
                    "require_approval": True
                })
                
                return {
                    "task_id": task_id,
                    "status": "pending_approval",
                    "plan": plan
                }
            else:
                # Execute workflow directly
                try:
                    result = await self.graph.ainvoke(state)
                    
                    # Store task information
                    self.storage.set(task_id, {
                        "id": task_id,
                        "status": "completed",
                        "request": request,
                        "created_at": datetime.utcnow(),
                        "require_approval": False,
                        "results": {
                            "diagnosis": result.get("diagnosis"),
                            "script": result.get("script"),
                            "email_draft": result.get("email_draft")
                        }
                    })
                    
                    return {
                        "task_id": task_id,
                        "status": "completed",
                        "results": {
                            "diagnosis": result.get("diagnosis"),
                            "script": result.get("script"),
                            "email_draft": result.get("email_draft")
                        }
                    }
                except Exception as e:
                    # Store task information with error
                    self.storage.set(task_id, {
                        "id": task_id,
                        "status": "failed",
                        "request": request,
                        "created_at": datetime.utcnow(),
                        "require_approval": False,
                        "errors": [str(e)]
                    })
                    
                    return {
                        "task_id": task_id,
                        "status": "failed",
                        "errors": [str(e)]
                    }
        except Exception as e:
            return {
                "status": "failed",
                "errors": [str(e)]
            }
    
    async def _create_plan(self, request: str) -> Dict[str, Any]:
        """Create a plan for the request."""
        try:
            # Use diagnostic agent to analyze the request
            analysis = await self.diagnostic_agent.execute({"task": request})
            if "error" in analysis:
                raise Exception(f"Diagnostic analysis failed: {analysis['error']}")
            return analysis
        except Exception as e:
            raise Exception(f"Failed to create plan: {str(e)}")