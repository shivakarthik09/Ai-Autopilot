import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.coordinator import Coordinator
from app.agents.diagnostic import DiagnosticAgent
from app.agents.automation import AutomationAgent
from app.agents.writer import WriterAgent
import json
import os
from dotenv import load_dotenv

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def coordinator():
    """Create a coordinator instance for testing."""
    return Coordinator()

@pytest.fixture
def diagnostic_agent():
    """Create a diagnostic agent instance for testing."""
    return DiagnosticAgent()

@pytest.fixture
def automation_agent():
    """Create an automation agent instance for testing."""
    return AutomationAgent(max_retries=3)

@pytest.fixture
def writer_agent():
    """Create a writer agent instance for testing."""
    return WriterAgent()

@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return {
        "task": "Fix database connection timeout issue",
        "priority": "high",
        "category": "database"
    }

@pytest.fixture
def sample_diagnosis():
    """Create a sample diagnosis for testing."""
    return {
        "root_cause": "Network latency causing connection timeouts",
        "evidence": [
            "Connection attempts timing out after 30 seconds",
            "High latency observed in network traces"
        ],
        "solutions": [
            {
                "description": "Increase connection timeout settings",
                "confidence": "high"
            },
            {
                "description": "Implement connection pooling",
                "confidence": "medium"
            }
        ]
    }

@pytest.fixture
def sample_script():
    """Create a sample PowerShell script for testing."""
    return {
        "script": """
# Increase SQL Server connection timeout
$configPath = "HKLM:\\SOFTWARE\\Microsoft\\MSSQLServer\\MSSQLServer"
Set-ItemProperty -Path $configPath -Name "ConnectionTimeout" -Value 60

# Test connection
$testConn = New-Object System.Data.SqlClient.SqlConnection
$testConn.ConnectionString = "Server=localhost;Database=master;Connection Timeout=60"
try {
    $testConn.Open()
    Write-Host "Connection successful"
} catch {
    Write-Error "Connection failed: $_"
} finally {
    $testConn.Close()
}
""",
        "verification_steps": [
            "Check registry value was updated",
            "Verify connection test succeeds"
        ],
        "expected_output": "Connection successful"
    }

@pytest.fixture
def sample_email():
    """Create a sample email draft for testing."""
    return {
        "subject": "Database Connection Timeout Resolution",
        "body": "We have identified and resolved the database connection timeout issue...",
        "key_points": [
            "Root cause: Network latency",
            "Solution implemented: Increased timeout settings"
        ],
        "action_items": [
            "Monitor connection performance",
            "Schedule follow-up review"
        ]
    }

@pytest.fixture
def mock_openai(monkeypatch):
    class MockOpenAI:
        def __init__(self):
            self.chat = self.Chat()
        
        class Chat:
            class Completions:
                @staticmethod
                async def create(*args, **kwargs):
                    return type('obj', (object,), {
                        'choices': [
                            type('obj', (object,), {
                                'message': type('obj', (object,), {
                                    'content': {
                                        "required_agents": ["DiagnosticAgent", "AutomationAgent", "WriterAgent"],
                                        "steps": ["Diagnose issue", "Generate script", "Create summary"],
                                        "summary": "Test plan"
                                    }
                                })
                            })
                        ]
                    })
            
            completions = Completions()
    
    monkeypatch.setattr("openai.OpenAI", MockOpenAI)
    return MockOpenAI()

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up the test environment before each test."""
    # Load environment variables
    load_dotenv()
    
    # Set test API key if not already set
    if not os.getenv("TOGETHER_API_KEY"):
        os.environ["TOGETHER_API_KEY"] = "test_api_key"
    
    yield
    
    # Clean up after each test
    # from app.coordinator import tasks  # Removed invalid import
    # tasks.clear()  # Commented out since tasks does not exist

@pytest.fixture
def sample_task(client):
    """Create a sample task for testing."""
    response = client.post(
        "/api/v1/execute",
        json={
            "request": "Test task",
            "require_approval": True
        }
    )
    return response.json() 