# Project Overview:
# This FastAPI microservice implements an agentic AI system for IT requests.
# It plans, orchestrates, and executes specialized LLM-powered agents (Coordinator, Diagnostic, Automation, Writer),
# supports approval workflows, and returns structured results. See README.md for full requirements and architecture.

"""
Agentic AI Service - FastAPI Microservice
This service processes IT requests through various specialized agents.
"""

import uvicorn
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Get port from environment or use default
    port = int(os.getenv("PORT", "8000"))
    
    # Start the server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True  # Enable auto-reload during development
    )

if __name__ == "__main__":
    main() 