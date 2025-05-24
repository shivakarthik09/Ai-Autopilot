import logging
import os

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/app.log", mode="a")
    ]
)

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from .coordinator import Coordinator
import json

app = FastAPI(title="Agentic AI API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize coordinator
coordinator = Coordinator()

class TaskRequest(BaseModel):
    request: str = Field(..., min_length=1, description="The request to process")
    require_approval: bool = Field(False, description="Whether the task requires approval")

class TaskResponse(BaseModel):
    task_id: str
    status: str
    plan: Optional[Dict[str, Any]] = None
    diagnosis: Optional[Dict[str, Any]] = None
    script: Optional[Dict[str, Any]] = None
    email_draft: Optional[str] = None
    duration_seconds: Optional[float] = None
    errors: Optional[List[str]] = None
    commands: List[str] = Field(default_factory=list)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

@app.post("/api/v1/execute", response_model=TaskResponse)
async def execute_task(request: TaskRequest):
    """Execute a task with optional approval requirement."""
    try:
        result = await coordinator.execute_task(request.request, request.require_approval)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/tasks/{task_id}/approve", response_model=TaskResponse)
async def approve_task(task_id: str):
    """Approve a task's plan."""
    try:
        result = await coordinator.approve_task(task_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/tasks/{task_id}/reject", response_model=TaskResponse)
async def reject_task(task_id: str):
    """Reject a task's plan."""
    try:
        result = await coordinator.reject_task(task_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Get a task by ID."""
    try:
        result = await coordinator.get_task(task_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tasks", response_model=List[TaskResponse])
async def list_tasks():
    """List all tasks."""
    try:
        result = await coordinator.list_tasks()
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/plans/{task_id}/approve", response_model=TaskResponse)
async def approve_plan(task_id: str):
    """Approve a plan (alias for /tasks/{task_id}/approve)."""
    return await approve_task(task_id)

@app.post("/api/v1/plans/{task_id}/reject", response_model=TaskResponse)
async def reject_plan(task_id: str):
    """Reject a plan (alias for /tasks/{task_id}/reject)."""
    return await reject_task(task_id) 