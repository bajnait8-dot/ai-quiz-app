"""LangGraph pipeline for quiz generation.

Evaluation is deliberately not part of the graph: scoring is deterministic and
quizzes are persisted in SQLite, so there is no in-memory thread state to lose.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.nodes.generate_quiz import gen_quiz_node
from agent.nodes.validate_input import validate_input_node
from agent.nodes.validate_quiz import validate_quiz_node
from agent.routers.post_input_validation_router import post_input_validation_router
from agent.state import State

workflow = StateGraph(State)

workflow.add_node("validate_input", validate_input_node)
workflow.add_node("generate", gen_quiz_node)
workflow.add_node("validate_quiz", validate_quiz_node)

workflow.add_edge(START, "validate_input")
workflow.add_conditional_edges(
    "validate_input",
    post_input_validation_router,
    {"generate": "generate", END: END},
)
workflow.add_edge("generate", "validate_quiz")
workflow.add_edge("validate_quiz", END)

quiz_agent = workflow.compile()
