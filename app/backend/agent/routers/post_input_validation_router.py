from __future__ import annotations

from langgraph.graph import END

from agent.state import State


def post_input_validation_router(state: State) -> str:
    return END if state.get("error") else "generate"
