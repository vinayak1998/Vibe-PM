"""Base agent: shared LLM call logic."""

from models.llm import llm_call
from models.schemas import ConversationState


class BaseAgent:
    """Shared logic for agents. Subclasses implement handle_message."""

    async def _llm_conversation(self, messages: list[dict], system_prompt: str) -> str:
        """Call conversation model with system + messages."""
        full = [{"role": "system", "content": system_prompt}] + messages
        return await llm_call("conversation", full)

    async def handle_message(
        self, state: ConversationState, user_message: str
    ) -> tuple[str, ConversationState]:
        """
        Process user message and return (response_text, updated_state).
        Subclasses override this.
        """
        raise NotImplementedError
