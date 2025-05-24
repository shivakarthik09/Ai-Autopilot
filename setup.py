from setuptools import setup, find_packages

setup(
    name="agentic-ai-fastapi",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "pydantic",
        "python-dotenv",
        "openai",
        "langgraph",
        "pytest",
        "httpx"
    ],
) 