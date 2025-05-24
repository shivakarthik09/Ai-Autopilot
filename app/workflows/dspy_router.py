import dspy
from typing import Dict, Any, List
from .task_router import TaskType
from app.utils.openai_client import OpenAIProjectClient
from app.config import OPENAI_API_KEY

class TaskAnalysis(dspy.Signature):
    """Analyze a task to determine its type and requirements."""
    task: str = dspy.InputField(desc="The task to analyze")
    task_type: str = dspy.OutputField(desc="The type of task (simple, complex, or critical)")
    required_agents: List[str] = dspy.OutputField(desc="List of required agents for the task")
    risk_level: str = dspy.OutputField(desc="The risk level of the task (low, medium, or high)")
    complexity: str = dspy.OutputField(desc="The complexity of the task (low or high)")

class TaskAnalyzer(dspy.Module):
    """Analyze tasks using chain of thought."""
    
    def __init__(self):
        super().__init__()
        self.analyzer = dspy.ChainOfThought("task -> task_type, required_agents, risk_level, complexity")
    
    async def forward(self, task: str) -> Dict[str, Any]:
        """Analyze a task and return its properties."""
        result = self.analyzer(task=task)
        return {
            "task_type": result.task_type,
            "required_agents": result.required_agents,
            "risk_level": result.risk_level,
            "complexity": result.complexity
        }

class DSPyRouter:
    """Route tasks using DSPy for analysis."""
    
    def __init__(self):
        # Initialize DSPy with our custom client
        self.client = OpenAIProjectClient(api_key=OPENAI_API_KEY)
        dspy.configure(lm=self.client)
        
        # Create task analyzer
        self.analyzer = TaskAnalyzer()
    
    async def analyze_task(self, task: str) -> Dict[str, Any]:
        """Analyze a task using DSPy and return the analysis."""
        try:
            # Get analysis from DSPy
            analysis = await self.analyzer(task)
            
            # Map task type to enum
            task_type_map = {
                "simple": TaskType.SIMPLE,
                "complex": TaskType.COMPLEX,
                "critical": TaskType.CRITICAL
            }
            
            # Convert task type to string
            task_type_str = analysis["task_type"].lower()
            if task_type_str not in task_type_map:
                task_type_str = "simple"  # Default to simple if unknown
            
            # Determine if approval is required
            requires_approval = self.should_require_approval(analysis)
            
            # Return structured output
            return {
                "task_type": task_type_str,
                "required_agents": analysis["required_agents"],
                "risk_level": analysis["risk_level"],
                "complexity": analysis["complexity"],
                "requires_approval": requires_approval
            }
        except Exception as e:
            # Return default analysis on error
            return {
                "task_type": "simple",
                "required_agents": ["DiagnosticAgent"],
                "risk_level": "low",
                "complexity": "low",
                "requires_approval": False
            }
    
    def should_require_approval(self, analysis: Dict[str, Any]) -> bool:
        """Determine if task requires approval based on analysis."""
        return (
            analysis["risk_level"] == "high" or
            analysis["complexity"] == "high" or
            "admin" in analysis["required_agents"].lower() or
            "root" in analysis["required_agents"].lower()
        ) 