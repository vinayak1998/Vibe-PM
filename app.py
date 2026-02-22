"""Chainlit entry point: session management, message handling, spec download."""

import chainlit as cl

from orchestrator import Orchestrator

# Phase -> display name for message author and thinking step
PHASE_AUTHOR = {
    "discovery": "Discovery",
    "scoping": "Scoping",
    "spec": "Spec Writer",
    "done": "PM",
}


@cl.on_chat_start
async def start():
    """Initialize orchestrator per session and send welcome message."""
    orchestrator = Orchestrator()
    cl.user_session.set("orchestrator", orchestrator)
    await cl.Message(
        content="Hi! I'm your AI PM. Tell me your product idea in a sentence or two, and I'll ask a few questions to understand the problem, scope an MVP, and then write you a product spec you can hand to a developer or code-gen tool."
    ).send()


@cl.on_message
async def main(message: cl.Message):
    """Route user message to orchestrator; send response and optional spec file."""
    orchestrator = cl.user_session.get("orchestrator")
    if orchestrator is None:
        await cl.Message(content="Session lost. Please refresh and start again.").send()
        return

    current_phase = orchestrator.state.phase
    agent_label = PHASE_AUTHOR.get(current_phase, "PM")

    async def step_callback(step_name: str):
        """Show a short 'work in progress' message so the user sees research/scoping work."""
        await cl.Message(content=step_name, author="PM").send()

    try:
        async with cl.Step(name=agent_label, type="run"):
            response, state = await orchestrator.handle_message(
                message.content or "", step_callback=step_callback
            )
    except ValueError as e:
        if "GROQ_API_KEY" in str(e):
            await cl.Message(
                content="GROQ_API_KEY is not set. Add it to a .env file in the project root (see .env.example)."
            ).send()
            return
        raise
    except Exception as e:
        await cl.Message(
            content=f"I'm having trouble thinking right now. Please try again. ({e!s})"
        ).send()
        return

    # Send the text response with author so user sees which agent responded
    await cl.Message(content=response, author=PHASE_AUTHOR[state.phase]).send()

    # If we just finished, offer the spec as a downloadable file
    if state.phase == "done" and state.spec_markdown:
        elements = [
            cl.File(
                name="product_spec.md",
                content=state.spec_markdown.encode("utf-8"),
                display="inline",
            )
        ]
        await cl.Message(
            content="Download your product spec:",
            elements=elements,
            author=PHASE_AUTHOR["done"],
        ).send()
