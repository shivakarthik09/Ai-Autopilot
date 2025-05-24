# Testing Guide

## Prerequisites
1. FastAPI server running on `http://localhost:8000`
2. Python 3.8+ installed
3. Required Python packages installed (see `requirements.txt`)

## Running Tests

### Using pytest
```bash
pytest tests/
```

### Running Specific Test Files
```bash
pytest tests/test_agent_retry.py
pytest tests/test_workflow.py
```

## Test Cases

### 1. Direct Execution (Example A)
- Verifies task completion without approval
- Checks for non-empty diagnosis and script sections
- Validates email draft format
- Confirms script linting passes

### 2. Approval Flow (Example B)
- Verifies initial "waiting_approval" status
- Tests approval process
- Validates final completion
- Checks generated Azure CLI commands

### 3. Agent Retry
- Simulates AutomationAgent failure
- Verifies Coordinator retry mechanism
- Tests graceful failure handling

### 4. Script Validation
- Verifies PowerShell script syntax
- Checks Bash script syntax
- Validates command structure

## Manual Testing

### Using the Batch File
```powershell
.\run_examples.bat
```

### Using curl
```bash
# Example A
curl -X POST "http://localhost:8000/api/v1/execute" \
     -H "Content-Type: application/json" \
     -d '{
           "request": "Diagnose why Windows Server 2019 VM cpu01 hits 95%+ CPU, generate a PowerShell script to collect perfmon logs, and draft an email to management summarising findings.",
           "require_approval": false
         }'

# Example B
curl -X POST "http://localhost:8000/api/v1/execute" \
     -H "Content-Type: application/json" \
     -d '{
           "request": "Create Azure CLI commands to lock RDP (3389) on my three production VMs to 10.0.0.0/24 and pause for approval before outputting the commands.",
           "require_approval": true
         }'
```

## Expected Results

### Example A
- Status should be "completed"
- Diagnosis should contain root cause and evidence
- Script should be valid PowerShell
- Email draft should be properly formatted

### Example B
- Initial status should be "waiting_approval"
- After approval, status should be "completed"
- Final response should include Azure CLI commands
- Email draft should be properly formatted

## Troubleshooting

### Common Issues
1. Server not running
   - Solution: Start FastAPI server
   - Command: `uvicorn app.main:app --reload`

2. Invalid task ID
   - Solution: Check task ID format
   - Format: UUID v4

3. Approval flow stuck
   - Solution: Check plan status
   - Command: `curl -X GET "http://localhost:8000/api/v1/tasks/{task_id}"`

4. Script validation fails
   - Solution: Check script syntax
   - Use PowerShell ISE or VS Code for validation

## Test Data
Test data and examples are available in:
- `docs/example_run.md`
- `docs/API_EXAMPLES.md`
- `postman_collection.json` 