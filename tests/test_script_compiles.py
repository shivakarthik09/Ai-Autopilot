import pytest
from fastapi.testclient import TestClient
from app.main import app
import json
import tempfile
import os
import subprocess

client = TestClient(app)

def test_script_compiles():
    """Test script compilation and validation for PowerShell, Azure CLI, and Bash"""
    # PowerShell
    response = client.post(
        "/api/v1/execute",
        json={
            "request": "Generate PowerShell script to get system information"
        }
    )
    assert response.status_code == 200
    data = response.json()
    print("DEBUG: status returned:", data["status"])
    assert data["status"] == "completed"
    # Only assert script if automation agent is required
    required_agents = []
    for key in ("plan", "analysis"):
        if key in data and data[key] and isinstance(data[key], dict):
            required_agents = data[key].get("required_agents", [])
            break
    if "automation" in required_agents:
        script = data["script"]
        assert script["language"] == "powershell"
        assert script["lint_passed"] is True
    # Azure CLI
    response = client.post(
        "/api/v1/execute",
        json={
            "request": "Generate Azure CLI commands to list VMs"
        }
    )
    assert response.status_code == 200
    data = response.json()
    print("DEBUG: status returned:", data["status"])
    # Print required_agents and completed_agents if available
    if "plan" in data and data["plan"]:
        print("DEBUG: plan:", data["plan"])
    if "script" in data and data["script"]:
        print("DEBUG: script:", data["script"])
    assert data["status"] == "completed"
    # Only assert script if automation agent is required
    required_agents = []
    for key in ("plan", "analysis"):
        if key in data and data[key] and isinstance(data[key], dict):
            required_agents = data[key].get("required_agents", [])
            break
    if "automation" in required_agents:
        script = data["script"]
        assert script["language"].lower() in ["azure cli", "bash"]
        assert script["lint_passed"] is True
    # Bash
    response = client.post(
        "/api/v1/execute",
        json={
            "request": "Generate Bash script to check disk usage"
        }
    )
    assert response.status_code == 200
    data = response.json()
    print("DEBUG: status returned:", data["status"])
    assert data["status"] == "completed"
    # Only assert script if automation agent is required
    required_agents = []
    for key in ("plan", "analysis"):
        if key in data and data[key] and isinstance(data[key], dict):
            required_agents = data[key].get("required_agents", [])
            break
    if "automation" in required_agents:
        script = data["script"]
        assert script["language"].lower() == "bash"
        assert script["lint_passed"] is True
    
    # Test PowerShell script compilation
    with tempfile.NamedTemporaryFile(suffix=".ps1", delete=False) as temp:
        temp.write(script["code"].encode())
        temp_path = temp.name
    
    try:
        result = subprocess.run(
            ["powershell", "-Command", f"Get-Command -Syntax '{temp_path}'"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
    finally:
        os.unlink(temp_path)
    
    # Test Bash script compilation
    with tempfile.NamedTemporaryFile(suffix=".sh", delete=False) as temp:
        temp.write(script["code"].encode())
        temp_path = temp.name
    
    try:
        result = subprocess.run(
            ["bash", "-n", temp_path],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
    finally:
        os.unlink(temp_path) 