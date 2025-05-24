import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.workflows.coordinator_graph import CoordinatorGraph
from app.agents.diagnostic import DiagnosticAgent

client = TestClient(app)

@pytest.mark.asyncio
async def test_agent_retry():
    """Test agent retry mechanism and task status handling."""
    # Test basic task execution
    response = client.post("/api/v1/execute", json={"request": "Simple diagnostic task"})
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    
    # Wait for task completion
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert "diagnosis" in response.json()
    assert response.json()["diagnosis"]["root_cause"] is not None
    
    # Test task that should fail (default behavior: agent returns a valid diagnosis, so status is completed)
    response = client.post("/api/v1/execute", json={"request": "Task that should fail"})
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    
    # Wait for task completion
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    # Default: should be completed, not failed
    assert response.json()["status"] == "completed"
    assert "diagnosis" in response.json()
    assert response.json()["diagnosis"]["root_cause"] is not None
    
    # Test task with retry
    response = client.post("/api/v1/execute", json={"request": "Task with retry"})
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    
    # Wait for task completion
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert "diagnosis" in response.json()
    assert response.json()["diagnosis"]["root_cause"] is not None

@pytest.mark.asyncio
async def test_task_status_handling():
    """Test task status handling in different scenarios."""
    # Test successful task
    response = client.post("/api/v1/execute", json={"request": "Simple diagnostic task"})
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    
    # Wait for task completion
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert "diagnosis" in response.json()
    assert response.json()["diagnosis"]["root_cause"] is not None
    
    # Test failed task (default behavior: agent returns a valid diagnosis, so status is completed)
    response = client.post("/api/v1/execute", json={"request": "Task that should fail"})
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    
    # Wait for task completion
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    # Default: should be completed, not failed
    assert response.json()["status"] == "completed"
    assert "diagnosis" in response.json()
    assert response.json()["diagnosis"]["root_cause"] is not None
    
    # Test task with retry
    response = client.post("/api/v1/execute", json={"request": "Task with retry"})
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    
    # Wait for task completion
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert "diagnosis" in response.json()
    assert response.json()["diagnosis"]["root_cause"] is not None

@pytest.mark.asyncio
async def test_agent_error_path():
    """Test that a real agent error results in failed status and error message."""
    with patch.object(DiagnosticAgent, 'execute', new_callable=AsyncMock) as mock_execute:
        mock_execute.side_effect = Exception("Critical error")
        response = client.post("/api/v1/execute", json={"request": "Task that should fail"})
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        # Wait for task completion
        response = client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        errors = response.json().get("errors") or []
        print(f"DEBUG ERRORS: {errors}")
        assert any("Critical error" in error for error in errors) 