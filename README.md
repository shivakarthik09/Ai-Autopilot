# Agentic AI FastAPI

An intelligent agent system built with FastAPI that processes IT requests through specialized AI agents.

## Features

- Intelligent request processing
- Approval workflow support
- Automated script generation
- Error handling and retry mechanisms
- Workflow orchestration
- LLM-powered agents

## Prerequisites

- Python 3.8+
- OpenAI API key
- Command-line tools (curl, PowerShell, or Bash)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/shivakarthik09/Ai-Autopilot.git
cd Ai-Autopilot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your OpenAI API key
```

## Running the Application

1. Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

2. Access the API at `http://localhost:8000`

## Testing the API

### Using the Batch File
```powershell
.\run_examples.bat
```

### Using curl
```bash
# Example A: Direct Execution
curl -X POST "http://localhost:8000/api/v1/execute" \
     -H "Content-Type: application/json" \
     -d '{
           "request": "Diagnose why Windows Server 2019 VM cpu01 hits 95%+ CPU, generate a PowerShell script to collect perfmon logs, and draft an email to management summarising findings.",
           "require_approval": false
         }'

# Example B: Approval Flow
curl -X POST "http://localhost:8000/api/v1/execute" \
     -H "Content-Type: application/json" \
     -d '{
           "request": "Create Azure CLI commands to lock RDP (3389) on my three production VMs to 10.0.0.0/24 and pause for approval before outputting the commands.",
           "require_approval": true
         }'
```

## Running Tests

```bash
pytest tests/
```

## Project Structure

```
Ai-Autopilot/
├── app/
│   ├── agents/
│   ├── workflows/
│   ├── utils/
│   ├── main.py
│   └── config.py
├── tests/
│   ├── test_agent_retry.py
│   └── test_workflow.py
├── docs/
│   ├── architecture.md
│   ├── API_EXAMPLES.md
│   ├── TESTING.md
│   └── example_run.md
├── requirements.txt
├── run_examples.bat
└── README.md
```

## Documentation

- [Architecture](docs/architecture.md)
- [API Examples](docs/API_EXAMPLES.md)
- [Testing Guide](docs/TESTING.md)
- [Example Run](docs/example_run.md)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.