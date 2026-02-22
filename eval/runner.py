"""Automated eval runner: run test conversations, collect transcripts, optional scoring."""

import asyncio
import sys
from pathlib import Path

# Add project root so imports work
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import yaml

from orchestrator import Orchestrator
from eval.rubric import RUBRIC_DIMENSIONS, get_rubric_text


SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"


def load_scenario(name: str) -> dict:
    """Load a scenario YAML by name (e.g. vague_founder)."""
    path = SCENARIOS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Scenario not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}


async def run_conversation(
    scenario_name: str,
    user_messages: list[str] | None = None,
    max_turns: int = 50,
) -> tuple[list[dict], dict]:
    """
    Run a single conversation with the orchestrator.
    If user_messages is provided, use those in order (and stop when exhausted).
    Otherwise use scenario initial_message only and then auto-respond (not implemented here).
    Returns (transcript, final_state_dict).
    """
    orchestrator = Orchestrator()
    transcript = []

    if user_messages is None:
        scenario = load_scenario(scenario_name)
        # Use full message sequence if provided; otherwise single initial message
        user_messages = scenario.get("messages") or [scenario.get("initial_message", "I have a product idea.")]

    for i, user_msg in enumerate(user_messages):
        if i >= max_turns:
            break
        try:
            response, state = await orchestrator.handle_message(user_msg)
        except Exception as e:
            transcript.append({"user": user_msg, "assistant": f"[ERROR: {e}]", "phase": "error"})
            break
        transcript.append({
            "user": user_msg,
            "assistant": response[:2000] + ("..." if len(response) > 2000 else ""),
            "phase": state.phase,
        })
        if state.phase == "done":
            break

    # Build state summary for scoring
    state = orchestrator.state
    state_dict = {
        "phase": state.phase,
        "discovery_summary": state.discovery_summary.model_dump() if state.discovery_summary else {},
        "scoping_output": state.scoping_output.model_dump() if state.scoping_output else None,
        "spec_length": len(state.spec_markdown or ""),
    }
    return transcript, state_dict


def format_transcript(transcript: list[dict]) -> str:
    """Format transcript for human or LLM review."""
    lines = []
    for t in transcript:
        lines.append(f"User: {t['user']}")
        lines.append(f"Assistant: {t['assistant']}")
        lines.append(f"[Phase: {t['phase']}]")
        lines.append("")
    return "\n".join(lines)


async def main():
    """Run all 5 scenarios and print transcripts. No LLM scoring (add separately if needed)."""
    scenario_names = ["vague_founder", "over_scoper", "clear_thinker", "arguer", "pivoter"]
    print(get_rubric_text())
    print("\n--- Running scenarios ---\n")

    for name in scenario_names:
        print(f"=== Scenario: {name} ===\n")
        try:
            transcript, state_dict = await run_conversation(name)
            print(format_transcript(transcript))
            print(f"Final phase: {state_dict['phase']}, spec length: {state_dict['spec_length']}\n")
        except Exception as e:
            print(f"Error: {e}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
