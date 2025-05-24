import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# Get OpenAI API key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000
API_RELOAD = True 