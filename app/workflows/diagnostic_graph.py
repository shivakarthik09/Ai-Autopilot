from typing import Dict, Any, List, TypedDict, Annotated, Union
from langgraph.graph import StateGraph, END
from app.agents.diagnostic import DiagnosticAgent, DiagnosisResult
import openai

class DiagnosticState(TypedDict):
    """State for diagnostic workflow."""
    task: str
    task_id: str
    current_stage: str
    diagnosis: Union[DiagnosisResult, None]
    error: Union[str, None]
    recursion_count: int

class DiagnosticGraph:
    """Graph for diagnostic workflow."""
    
    def __init__(self):
        self.agent = DiagnosticAgent()
        self.max_recursions = 5
    
    def create_graph(self) -> StateGraph:
        """Create the diagnostic workflow graph."""
        workflow = StateGraph(DiagnosticState)
        workflow.add_node("initial_analysis", self._initial_analysis)
        workflow.add_node("deep_analysis", self._deep_analysis)
        workflow.add_node("solution_generation", self._solution_generation)
        workflow.add_node("confidence_check", self._confidence_check)
        workflow.add_node("finalize_diagnosis", self._finalize_diagnosis)
        workflow.add_conditional_edges(
            "initial_analysis",
            self._should_deep_analyze,
            {
                True: "deep_analysis",
                False: "solution_generation"
            }
        )
        workflow.add_conditional_edges(
            "confidence_check",
            self._is_confidence_sufficient,
            {
                True: "finalize_diagnosis",
                False: "deep_analysis"
            }
        )
        workflow.add_edge("deep_analysis", "solution_generation")
        workflow.add_edge("solution_generation", "confidence_check")
        workflow.add_edge("finalize_diagnosis", END)
        workflow.set_entry_point("initial_analysis")
        return workflow.compile()

    async def _increment_recursion(self, state: DiagnosticState) -> DiagnosticState:
        count = state.get("recursion_count", 0) + 1
        return {**state, "recursion_count": count}

    async def _initial_analysis(self, state: DiagnosticState) -> DiagnosticState:
        state = await self._increment_recursion(state)
        try:
            diagnosis = await self.agent.execute({"task": state["task"]})
            return {**state, "current_stage": "initial_analysis", "diagnosis": diagnosis, "error": None}
        except Exception as e:
            return {**state, "current_stage": "initial_analysis", "error": str(e)}

    async def _deep_analysis(self, state: DiagnosticState) -> DiagnosticState:
        state = await self._increment_recursion(state)
        try:
            context = {
                "task": state["task"],
                "initial_diagnosis": state["diagnosis"]
            }
            diagnosis = await self.agent.execute(context)
            return {**state, "current_stage": "deep_analysis", "diagnosis": diagnosis, "error": None}
        except Exception as e:
            return {**state, "current_stage": "deep_analysis", "error": str(e)}

    async def _solution_generation(self, state: DiagnosticState) -> DiagnosticState:
        state = await self._increment_recursion(state)
        try:
            context = {
                "task": state["task"],
                "diagnosis": state["diagnosis"]
            }
            diagnosis = await self.agent.execute(context)
            return {**state, "current_stage": "solution_generation", "diagnosis": diagnosis, "error": None}
        except Exception as e:
            return {**state, "current_stage": "solution_generation", "error": str(e)}

    async def _confidence_check(self, state: DiagnosticState) -> DiagnosticState:
        state = await self._increment_recursion(state)
        try:
            context = {
                "task": state["task"],
                "diagnosis": state["diagnosis"]
            }
            diagnosis = await self.agent.execute(context)
            return {**state, "current_stage": "confidence_check", "diagnosis": diagnosis, "error": None}
        except Exception as e:
            return {**state, "current_stage": "confidence_check", "error": str(e)}

    async def _finalize_diagnosis(self, state: DiagnosticState) -> DiagnosticState:
        state = await self._increment_recursion(state)
        try:
            context = {
                "task": state["task"],
                "diagnosis": state["diagnosis"]
            }
            diagnosis = await self.agent.execute(context)
            return {**state, "current_stage": "finalize_diagnosis", "diagnosis": diagnosis, "error": None}
        except Exception as e:
            return {**state, "current_stage": "finalize_diagnosis", "error": str(e)}

    def _should_deep_analyze(self, state: DiagnosticState) -> bool:
        # If recursion count exceeded, force solution generation
        if state.get("recursion_count", 0) >= self.max_recursions:
            return False
        if state.get("error"):
            return False
        diagnosis = state.get("diagnosis")
        if not diagnosis:
            return True
        return getattr(diagnosis, "complexity", "low") == "high" or getattr(diagnosis, "risk_level", "low") == "high"

    def _is_confidence_sufficient(self, state: DiagnosticState) -> bool:
        # If recursion count exceeded, force finalize
        if state.get("recursion_count", 0) >= self.max_recursions:
            return True
        if state.get("error"):
            return True
        diagnosis = state.get("diagnosis")
        if not diagnosis:
            return False
        # Defensive: if solutions missing, finalize
        solutions = getattr(diagnosis, "solutions", [])
        if not solutions:
            return True
        return all(getattr(sol, "confidence", 1.0) >= 0.8 for sol in solutions)

    async def execute(self, task: str, task_id: str) -> Dict[str, Any]:
        """Execute the diagnostic workflow."""
        state = {
            "task": task,
            "task_id": task_id,
            "current_stage": "initial_analysis",
            "diagnosis": None,
            "error": None,
            "recursion_count": 0
        }
        graph = self.create_graph()
        final_state = await graph.ainvoke(state)
        return final_state 