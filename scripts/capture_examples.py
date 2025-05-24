import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

def to_serializable(obj):
    # Convert Pydantic models to dicts
    if hasattr(obj, 'dict'):
        return obj.dict()
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    if isinstance(obj, list):
        return [to_serializable(i) for i in obj]
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    return obj

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

import dspy
from app.workflows.dspy_router import DSPyRouter
from app.workflows.coordinator_graph import CoordinatorGraph
from app.workflows.diagnostic_graph import DiagnosticGraph
from app.workflows.context_pruner import ContextPruner

async def capture_examples():
    """Capture example flows for documentation."""
    print("Starting example capture...")
    
    try:
        # Initialize components
        router = DSPyRouter()
        coordinator = CoordinatorGraph()
        diagnostic = DiagnosticGraph()
        pruner = ContextPruner()
        
        # Example 1: Investigate high CPU usage on server
        print("\nExample 1: Investigate high CPU usage on server")
        task1 = "Investigate high CPU usage on server"
        task1_id = str(uuid.uuid4())
        analysis1 = router.analyze_task(task1)
        print("Analysis:", analysis1)
        
        # Execute diagnostic workflow
        result1 = await diagnostic.execute(task1, task1_id)
        print(f"Diagnostic Result: {json.dumps(to_serializable(result1), indent=2)}")
        
        # Example 2: Automate backup script
        print("\nExample 2: Automate backup script")
        task2 = "Automate backup script for database"
        task2_id = str(uuid.uuid4())
        analysis2 = router.analyze_task(task2)
        print("Analysis:", analysis2)
        
        # Execute full workflow
        result2 = await coordinator.execute(task2, task2_id)
        print(f"Workflow Result: {json.dumps(to_serializable(result2), indent=2)}")
        
        # Example 3: Draft incident report email
        print("\nExample 3: Draft incident report email")
        task3 = "Draft incident report email for recent outage"
        task3_id = str(uuid.uuid4())
        analysis3 = router.analyze_task(task3)
        print("Analysis:", analysis3)
        
        # Context pruning
        context = {
            "task": task2,
            "analysis": analysis2,
            "diagnostic_result": result1,
            "workflow_result": result2
        }
        
        pruned = await pruner.prune_context(context)
        print(f"\nExample 3: Context Pruning")
        print(f"Original size: {len(str(context))} chars")
        print(f"Pruned size: {len(str(pruned))} chars")
        
        # Save examples
        examples_dir = Path("docs/examples")
        examples_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        examples_file = examples_dir / f"example_flows_{timestamp}.json"
        
        examples = {
            "example1": {
                "task": task1,
                "task_id": task1_id,
                "analysis": analysis1,
                "result": to_serializable(result1)
            },
            "example2": {
                "task": task2,
                "task_id": task2_id,
                "analysis": analysis2,
                "result": to_serializable(result2)
            },
            "example3": {
                "original_context": to_serializable(context),
                "pruned_context": to_serializable(pruned)
            }
        }
        
        with open(examples_file, "w") as f:
            json.dump(examples, f, indent=2)
        
        print(f"\nExamples saved to {examples_file}")
        
    except Exception as e:
        print(f"Error during example capture: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(capture_examples()) 