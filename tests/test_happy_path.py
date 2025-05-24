import pytest
from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)

def test_happy_path():
    """Test Example A: Happy path for direct execution"""
    response = client.post(
        "/api/v1/execute",
        json={
            "request": "Diagnose high CPU usage on a Windows Server VM"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "completed"
    assert "diagnosis" in data
    assert "script" in data
    assert "email_draft" in data
    diagnosis = data["diagnosis"]
    assert isinstance(diagnosis, dict)
    assert "root_cause" in diagnosis
    assert "evidence" in diagnosis
    assert "solutions" in diagnosis
    script = data["script"]
    assert isinstance(script, dict)
    assert script["language"] == "powershell"
    assert script["lint_passed"] is True
    assert "code" in script
    email = data["email_draft"]
    assert isinstance(email, str)
    assert "Subject:" in email
    assert "Dear" in email 