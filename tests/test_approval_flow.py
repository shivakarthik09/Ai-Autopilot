import pytest
from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)

def test_approval_flow():
    """Test Example B: Approval workflow for critical task"""
    # Make request requiring approval
    response = client.post(
        "/api/v1/execute",
        json={
            "request": "Create Azure CLI commands to lock RDP on production VMs",
            "require_approval": True
        }
    )
    
    # Check initial response
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "waiting_approval"
    assert "plan" in data
    assert isinstance(data["plan"], dict)
    assert "steps" in data["plan"]
    assert "summary" in data["plan"]
    
    # Get task ID and check status
    task_id = data["task_id"]
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "waiting_approval"
    
    # Approve the plan
    response = client.post(
        f"/api/v1/tasks/{task_id}/approve",
        json={"approved": True}
    )
    assert response.status_code == 200
    
    # Check final status
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert data["status"] == "completed"
    assert "script" in data
    assert "commands" in data
    assert "email_draft" in data
    
    # Verify script structure
    script = data["script"]
    assert isinstance(script, dict)
    assert "language" in script
    assert "code" in script
    assert "lint_passed" in script
    assert script["language"] == "powershell"
    assert script["lint_passed"] is True
    
    # Verify commands
    assert isinstance(data["commands"], list)
    assert len(data["commands"]) > 0
    for cmd in data["commands"]:
        assert isinstance(cmd, str)
        assert "az vm" in cmd.lower()
        assert any(kw in cmd.lower() for kw in ["lock", "disable", "enable", "set"])
    
    # Verify email draft
    assert isinstance(data["email_draft"], str)
    assert "Subject:" in data["email_draft"]
    assert "Dear" in data["email_draft"] 