import asyncio
import json
import sys
from pathlib import Path
import time
from datetime import datetime

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from app.main import app
from fastapi.testclient import TestClient

def print_section(title):
    print("\n" + "="*80)
    print(f" {title} ".center(80, "="))
    print("="*80 + "\n")

def print_json(data):
    print(json.dumps(data, indent=2))

def run_examples():
    """Run and demonstrate Example A and B flows."""
    # Initialize test client with the correct syntax
    client = TestClient(app=app)
    
    # Example A: Direct Execution
    print_section("Example A: Direct Execution")
    print("Request:")
    request_a = {
        "request": "Diagnose why Windows Server 2019 VM cpu01 hits 95%+ CPU, generate a PowerShell script to collect perfmon logs, and draft an email to management summarising findings.",
        "require_approval": False
    }
    print_json(request_a)
    
    print("\nResponse:")
    response_a = client.post("/api/v1/execute", json=request_a)
    print_json(response_a.json())
    
    # Wait for completion
    task_id_a = response_a.json()["task_id"]
    max_retries = 5
    for i in range(max_retries):
        status = client.get(f"/api/v1/tasks/{task_id_a}")
        status_data = status.json()
        if status_data.get("status") == "completed":
            print("\nFinal Status:")
            print_json(status_data)
            break
        elif status_data.get("status") == "failed":
            print("\nTask Failed:")
            print_json(status_data)
            break
        time.sleep(1)
    
    # Example B: Approval Flow
    print_section("Example B: Approval Flow")
    print("Initial Request:")
    request_b = {
        "request": "Create Azure CLI commands to lock RDP (3389) on my three production VMs to 10.0.0.0/24 and pause for approval before outputting the commands.",
        "require_approval": True
    }
    print_json(request_b)
    
    print("\nInitial Response:")
    response_b = client.post("/api/v1/execute", json=request_b)
    print_json(response_b.json())
    
    # Get task ID and approve
    task_id_b = response_b.json()["task_id"]
    print("\nApproving task...")
    approve_response = client.post(f"/api/v1/tasks/{task_id_b}/approve")
    print("\nApproval Response:")
    print_json(approve_response.json())
    
    # Wait for completion
    max_retries = 5
    for i in range(max_retries):
        status = client.get(f"/api/v1/tasks/{task_id_b}")
        status_data = status.json()
        if status_data.get("status") == "completed":
            print("\nFinal Status:")
            print_json(status_data)
            break
        elif status_data.get("status") == "failed":
            print("\nTask Failed:")
            print_json(status_data)
            break
        time.sleep(1)

if __name__ == "__main__":
    run_examples() 