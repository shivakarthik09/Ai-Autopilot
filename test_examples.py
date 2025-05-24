import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_example_a():
    print("\nTesting Example A - Direct Execution (No Approval)")
    
    # Example A request
    payload = {
        "request": "Diagnose why Windows Server 2019 VM cpu01 hits 95%+ CPU, generate a PowerShell script to collect perfmon logs, and draft an email to management summarising findings.",
        "require_approval": False
    }
    
    # Make the request
    response = requests.post(f"{BASE_URL}/execute", json=payload)
    print(f"Response Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\nResponse:")
        print(json.dumps(result, indent=2))
        
        # Verify required fields
        assert result["status"] == "completed", "Status should be completed"
        assert "diagnosis" in result, "Should have diagnosis"
        assert "script" in result, "Should have script"
        assert "email_draft" in result, "Should have email_draft"
        print("\nExample A test passed!")
    else:
        print(f"Error: {response.text}")

def test_example_b():
    print("\nTesting Example B - Approval Flow")
    
    # Example B request
    payload = {
        "request": "Create Azure CLI commands to lock RDP (3389) on my three production VMs to 10.0.0.0/24 and pause for approval before outputting the commands.",
        "require_approval": True
    }
    
    # Make initial request
    response = requests.post(f"{BASE_URL}/execute", json=payload)
    print(f"Initial Response Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\nInitial Response:")
        print(json.dumps(result, indent=2))
        
        # Verify waiting for approval
        assert result["status"] == "waiting_approval", "Status should be waiting_approval"
        assert "plan" in result, "Should have plan"
        
        # Get task ID
        task_id = result["task_id"]
        
        # Approve the plan
        print("\nApproving plan...")
        approve_response = requests.post(f"{BASE_URL}/tasks/{task_id}/approve")
        print(f"Approval Response Status: {approve_response.status_code}")
        
        if approve_response.status_code == 200:
            final_result = approve_response.json()
            print("\nFinal Response after approval:")
            print(json.dumps(final_result, indent=2))
            
            # Verify completion
            assert final_result["status"] == "completed", "Status should be completed"
            assert "commands" in final_result, "Should have commands"
            print("\nExample B test passed!")
        else:
            print(f"Error during approval: {approve_response.text}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    print("Starting API tests...")
    test_example_a()
    test_example_b() 