import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import app
sys.path.append(str(Path(__file__).parent.parent))
from app.main import app
from fastapi.testclient import TestClient

def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")

def print_json(data):
    """Print JSON data with formatting."""
    print(json.dumps(data, indent=2))

def save_demonstration():
    """Run and save the demonstration of Example A and B flows."""
    # Initialize test client
    client = TestClient(app)
    
    # Create output directory if it doesn't exist
    output_dir = Path(__file__).parent.parent / "docs" / "examples"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"demonstration_{timestamp}.md"
    
    with open(output_file, "w") as f:
        def write_section(title):
            f.write(f"\n## {title}\n\n")
        
        def write_json(data):
            f.write("```json\n")
            f.write(json.dumps(data, indent=2))
            f.write("\n```\n\n")
        
        # Example A: Direct Execution
        write_section("Example A: Direct Execution")
        f.write("### Request\n\n")
        request_a = {
            "request": "Diagnose why Windows Server 2019 VM cpu01 hits 95%+ CPU, generate a PowerShell script to collect perfmon logs, and draft an email to management summarising findings.",
            "require_approval": False
        }
        write_json(request_a)
        
        f.write("### Response\n\n")
        response_a = client.post("/api/v1/execute", json=request_a)
        write_json(response_a.json())
        
        # Wait for completion
        task_id_a = response_a.json()["task_id"]
        max_retries = 5
        for i in range(max_retries):
            status = client.get(f"/api/v1/tasks/{task_id_a}")
            status_data = status.json()
            if status_data.get("status") == "completed":
                f.write("### Final Status\n\n")
                write_json(status_data)
                break
            elif status_data.get("status") == "failed":
                f.write("### Task Failed\n\n")
                write_json(status_data)
                break
            time.sleep(1)
        
        # Example B: Approval Flow
        write_section("Example B: Approval Flow")
        f.write("### Initial Request\n\n")
        request_b = {
            "request": "Create Azure CLI commands to lock RDP (3389) on my three production VMs to 10.0.0.0/24 and pause for approval before outputting the commands.",
            "require_approval": True
        }
        write_json(request_b)
        
        f.write("### Initial Response\n\n")
        response_b = client.post("/api/v1/execute", json=request_b)
        write_json(response_b.json())
        
        # Get task ID and approve
        task_id_b = response_b.json()["task_id"]
        f.write("### Approval Request\n\n")
        approve_response = client.post(f"/api/v1/tasks/{task_id_b}/approve")
        f.write("### Approval Response\n\n")
        write_json(approve_response.json())
        
        # Wait for completion
        max_retries = 5
        for i in range(max_retries):
            status = client.get(f"/api/v1/tasks/{task_id_b}")
            status_data = status.json()
            if status_data.get("status") == "completed":
                f.write("### Final Status\n\n")
                write_json(status_data)
                break
            elif status_data.get("status") == "failed":
                f.write("### Task Failed\n\n")
                write_json(status_data)
                break
            time.sleep(1)
    
    print(f"\nDemonstration saved to: {output_file}")
    return output_file

if __name__ == "__main__":
    output_file = save_demonstration()
    print(f"\nTo view the demonstration, open: {output_file}") 