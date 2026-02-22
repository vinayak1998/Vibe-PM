"""Orchestrator: phase manager, handoff messages, skip prevention. Routes Discovery -> Scoping -> Spec -> Done."""

from typing import Awaitable, Callable, Optional

from models.schemas import ConversationState
from agents.discovery import DiscoveryAgent
from agents.scoping import ScopingAgent
from agents.spec_writer import SpecWriterAgent


HANDOFF_MESSAGES = {
    "discovery_to_scoping": (
        "Discovery is complete. I'm now handing off to the Scoping Agent, who will "
        "research comparable products, propose a phased MVP scope with RICE-scored features, "
        "and work with you to finalize the build plan."
    ),
    "scoping_to_spec": (
        "Scope is agreed. I'm now handing off to the Spec Writer, who will produce a "
        "detailed, phased product spec you can feed directly into a code generation tool."
    ),
}

SKIP_PREVENTION_MESSAGE = (
    "Sticking to the plan will get you the best result: discovery first, then scoping, then the spec. "
    "Going through each step with the AI will make the final spec much more useful. "
    "Let's continue from where we are — if you're in discovery, I'll keep asking; if you're in scoping, we'll lock the scope next."
)


def _user_wants_to_skip(user_message: str, phase: str) -> bool:
    """Heuristic: did the user ask to skip steps?"""
    if phase == "done":
        return False
    msg = (user_message or "").strip().lower()
    skip_phrases = (
        "just write the spec",
        "skip to spec",
        "skip discovery",
        "skip scoping",
        "skip to the spec",
        "go straight to spec",
        "only need the spec",
        "just give me the spec",
    )
    return any(p in msg for p in skip_phrases)


class Orchestrator:
    """
    Sequential phase manager: Discovery -> Scoping -> Spec -> Done.
    Explicit handoff messages at each transition. Skip prevention when user tries to jump ahead.
    step_callback(name) shows "work in progress" in the UI.
    """

    def __init__(self):
        self.state = ConversationState()
        self.discovery_agent = DiscoveryAgent()
        self.scoping_agent = ScopingAgent()
        self.spec_writer_agent = SpecWriterAgent()

    async def handle_message(
        self,
        user_message: str,
        step_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> tuple[str, ConversationState]:
        """
        Route to active agent. On phase transition, show handoff message and trigger next agent.
        If user tries to skip steps, return skip-prevention message.
        """
        state = self.state
        phase = state.phase

        if _user_wants_to_skip(user_message, phase):
            return SKIP_PREVENTION_MESSAGE, state

        if phase == "discovery":
            response, new_state = await self.discovery_agent.handle_message(state, user_message)
            self.state = new_state
            if new_state.phase == "scoping":
                if step_callback:
                    await step_callback("Researching comparable products and preparing scope…")
                handoff = HANDOFF_MESSAGES["discovery_to_scoping"]
                scoping_response, new_state = await self.scoping_agent.handle_message(
                    self.state, ""
                )
                self.state = new_state
                return f"{handoff}\n\n---\n\n{scoping_response}", self.state
            return response, self.state

        if phase == "scoping":
            response, new_state = await self.scoping_agent.handle_message(state, user_message)
            self.state = new_state
            if new_state.phase == "spec":
                if step_callback:
                    await step_callback("Writing your phased product spec…")
                handoff = HANDOFF_MESSAGES["scoping_to_spec"]
                spec_response, new_state = await self.spec_writer_agent.handle_message(
                    self.state, ""
                )
                self.state = new_state
                return f"{handoff}\n\n---\n\n{spec_response}", self.state
            return response, self.state

        if phase == "spec":
            response, new_state = await self.spec_writer_agent.handle_message(state, user_message)
            self.state = new_state
            return response, self.state

        return (
            "We're done! You can download your spec below or start a new conversation.",
            self.state,
        )
