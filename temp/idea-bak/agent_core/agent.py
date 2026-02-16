from agent_core.intent_classifier import classify_intent
from agent_core.intent_router import IntentRouter

class Agent:
    """
    Central orchestration class for the Intent-Driven Enterprise Assistant.
    All entry points (UI, API, scripts) must call `handle()`.
    """

    def __init__(self):
        self.router = IntentRouter()

    def handle(self, user_input: str):
        """
        Unified entry point for:
        - Streamlit UI
        - FastAPI Agent API
        - curl / Swagger
        - Python scripts

        :param user_input: Free-text user request
        :return: Capability response (invoice data or explanation)
        """
        if not user_input or not user_input.strip():
            raise ValueError("Input cannot be empty")

        intent = classify_intent(user_input)
        return self.router.route(intent)
