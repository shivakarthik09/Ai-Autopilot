from typing import List, Dict, Any
from enum import Enum

class TaskType(Enum):
    SIMPLE = "simple"
    COMPLEX = "complex"
    CRITICAL = "critical"

class TaskRouter:
    def __init__(self):
        # Define keywords for task classification
        self.simple_keywords = [
            "check", "verify", "read", "list", "show",
            "get", "find", "search", "query", "status"
        ]
        
        self.complex_keywords = [
            "analyze", "investigate", "diagnose", "monitor",
            "script", "automate", "generate", "create",
            "document", "report", "email", "notify"
        ]
        
        self.critical_keywords = [
            "delete", "remove", "uninstall", "drop", "truncate",
            "shutdown", "restart", "reboot", "format", "wipe",
            "production", "prod", "critical", "important",
            "admin", "root", "system", "security"
        ]
    
    def determine_task_type(self, task: str) -> TaskType:
        """Determine the type of task based on keywords and complexity."""
        task = task.lower()
        
        # Count keyword matches for each type
        simple_score = sum(1 for kw in self.simple_keywords if kw in task)
        complex_score = sum(1 for kw in self.complex_keywords if kw in task)
        critical_score = sum(1 for kw in self.critical_keywords if kw in task)
        
        # Return the type with highest score
        scores = {
            TaskType.SIMPLE: simple_score,
            TaskType.COMPLEX: complex_score,
            TaskType.CRITICAL: critical_score
        }
        
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def get_required_agents(self, task: str) -> List[str]:
        """Determine which agents are required for the task."""
        task_type = self.determine_task_type(task)
        
        if task_type == TaskType.CRITICAL:
            return ["diagnostic", "automation", "writer"]
        elif task_type == TaskType.COMPLEX:
            return ["diagnostic", "automation", "writer"]
        else:
            return ["diagnostic"]
    
    def should_require_approval(self, task: str) -> bool:
        """Determine if the task should require approval."""
        task = task.lower()
        
        # Check for read operations that should not require approval
        read_operations = [
            "get-", "show-", "list-", "query", "status", 
            "check", "verify", "read", "find", "search",
            "analyze", "investigate", "diagnose", "monitor",
            "generate", "create", "script"  # Adding script generation as read operation
        ]
        
        # If it's a read operation or script generation, no approval needed
        if any(kw in task for kw in read_operations):
            return False
            
        # Check for critical keywords that always require approval
        critical_keywords = [
            "delete", "remove", "uninstall", "drop", "truncate",
            "shutdown", "restart", "reboot", "format", "wipe",
            "lock", "disable", "enable"
        ]
        
        # If it contains critical keywords, approval needed
        if any(kw in task for kw in critical_keywords):
            return True
        
        # Check for system modification commands
        system_mod_commands = [
            "set-", "remove-", "delete-", "uninstall-",
            "format", "wipe", "clear", "reset", "lock",
            "disable", "enable", "restart", "shutdown"
        ]
        
        # Only require approval for actual modification commands
        if any(cmd in task for cmd in system_mod_commands):
            return True
        
        # Check for production/critical environment keywords
        prod_keywords = ["production", "prod", "critical", "important", "admin", "root", "system", "security"]
        if any(kw in task for kw in prod_keywords):
            # If it's a read operation in production, no approval needed
            if any(kw in task for kw in read_operations):
                return False
            return True
        
        return False
    
    def analyze_task(self, task: str) -> Dict[str, Any]:
        """Analyze the task and return a complete analysis."""
        task_type = self.determine_task_type(task)
        
        return {
            "task_type": task_type.value,
            "required_agents": self.get_required_agents(task),
            "requires_approval": self.should_require_approval(task),
            "complexity": "high" if task_type in [TaskType.COMPLEX, TaskType.CRITICAL] else "low",
            "risk_level": "high" if task_type == TaskType.CRITICAL else "medium" if task_type == TaskType.COMPLEX else "low"
        } 