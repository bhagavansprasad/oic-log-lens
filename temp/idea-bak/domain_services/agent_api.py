from fastapi import APIRouter, HTTPException
from agent_core.agent import Agent

router = APIRouter()
agent = Agent()


@router.post("/agent/handle")
def handle_request(payload: dict):
    user_input = payload.get("input")

    if not user_input:
        raise HTTPException(
            status_code=400,
            detail="input is required"
        )

    return agent.handle(user_input)
