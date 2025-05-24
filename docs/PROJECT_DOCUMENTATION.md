# Agentic AI FastAPI Project Documentation

## Project Overview
This project implements an agentic AI system as a FastAPI microservice that processes IT requests through specialized AI agents. The system uses LangGraph for workflow orchestration and integrates with LLMs for intelligent processing.

## Architecture

### Core Components

1. **API Layer** (`app/main.py`)
   - Implements FastAPI endpoints for request processing
   - Handles task execution, approval workflows, and status tracking
   - Key endpoints:
     - POST `/api/v1/execute`: Process new requests
     - POST `/api/v1/plans/{id}/approve`: Approve pending plans
     - POST `/api/v1/plans/{id}/reject`: Reject pending plans
     - GET `/api/v1/tasks/{id}`: Get task status and results

2. **Agent Layer** (`app/agents/`)
   - **CoordinatorAgent**: Orchestrates the overall execution flow
   - **DiagnosticAgent**: Performs root-cause analysis
   - **AutomationAgent**: Generates and validates scripts
   - **WriterAgent**: Creates structured content from results

3. **Workflow Layer** (`app/workflows/`)
   - Implements LangGraph-based workflow orchestration
   - `CoordinatorGraph`: Manages the overall execution flow
   - Specialist graphs for specific agent types

4. **Configuration** (`app/config.py`)
   - Manages application settings and environment variables
   - Configures LLM integration and other system parameters

## Key Files and Their Purposes

### Main Application Files

1. `app/main.py`
   - Entry point for the FastAPI application
   - Defines API routes and request handlers
   - Implements task management and status tracking

2. `app/coordinator.py`
   - Implements the CoordinatorAgent logic
   - Manages task planning and execution
   - Handles result merging and error management

3. `app/workflows/coordinator_graph.py`
   - Defines the LangGraph workflow for task execution
   - Implements conditional logic for agent selection
   - Manages the flow between different agents

### Testing Files

1. `tests/test_agent_retry.py`
   - Tests the agent retry mechanism
   - Verifies task status handling
   - Tests error path scenarios

2. `test_examples.py`
   - Contains example test cases
   - Demonstrates API usage patterns

### Support Files

1. `requirements.txt`
   - Lists project dependencies
   - Specifies version requirements

2. `setup.py`
   - Package configuration
   - Installation settings

3. `postman_collection.json`
   - API testing collection
   - Example requests and responses

## Challenges and Solutions

### 1. Task Status Management
**Challenge**: Ensuring consistent task status updates across different execution paths.
**Solution**: Implemented a centralized status management system with clear state transitions.

### 2. Error Handling
**Challenge**: Managing errors across multiple agents and maintaining context.
**Solution**: Created a robust error handling system with detailed error tracking and retry mechanisms.

### 3. Workflow Orchestration
**Challenge**: Coordinating multiple agents with different execution requirements.
**Solution**: Used LangGraph to create a flexible workflow system with conditional execution paths.

### 4. Testing Complexity
**Challenge**: Testing asynchronous operations and complex workflows.
**Solution**: Implemented comprehensive test cases with proper mocking and async support.

## Setup and Usage

1. **Installation**
   ```bash
   pip install -r requirements.txt
   ```

2. **Running the Application**
   ```bash
   python run.py
   ```

3. **Running Tests**
   ```bash
   pytest tests/
   ```

## API Examples

### Example A: Direct Execution
```json
POST /api/v1/execute
{
  "request": "Diagnose why Windows Server 2019 VM cpu01 hits 95%+ CPU",
  "require_approval": false
}
```

### Example B: Approval Flow
```json
POST /api/v1/execute
{
  "request": "Create Azure CLI commands to lock RDP",
  "require_approval": true
}
```

## Future Improvements

1. Enhanced error recovery mechanisms
2. Additional specialized agents
3. Improved monitoring and logging
4. Extended test coverage
5. Performance optimizations

## Conclusion
The project successfully implements an agentic AI system with robust workflow management and error handling. While there were challenges in implementation, the solutions provide a solid foundation for future enhancements. 