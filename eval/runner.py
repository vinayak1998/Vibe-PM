"""Automated eval runner: run test conversations, collect transcripts, optional scoring."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

# Add project root so imports work
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import yaml

from orchestrator import Orchestrator
from eval.rubric import RUBRIC_DIMENSIONS, get_rubric_text
from eval.simulated_user import SimulatedUser
from eval.assertions import run_assertions, print_checklist


SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"
TRANSCRIPTS_DIR = Path(__file__).resolve().parent / "transcripts"

# Seconds to wait between turns to avoid Groq free-tier TPM rate limits
TURN_DELAY_SECONDS = 20


def load_scenario(name: str) -> dict:
    """Load a scenario YAML by name (e.g. vague_founder)."""
    path = SCENARIOS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Scenario not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _save_transcript(scenario_name: str, transcript: List[dict], state_dict: dict) -> Path:
    """Save transcript and state to eval/transcripts/{scenario_name}_{timestamp}.yaml."""
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = TRANSCRIPTS_DIR / f"{scenario_name}_{timestamp}.yaml"
    payload = {"scenario": scenario_name, "transcript": transcript, "final_state": state_dict}
    with open(path, "w") as f:
        yaml.dump(payload, f, default_flow_style=False, allow_unicode=True)
    return path


def _phases_visited(transcript: List[dict]) -> List[str]:
    """Return deduplicated ordered list of phases seen across the transcript."""
    seen = []
    for turn in transcript:
        phase = turn.get("phase")
        if phase and (not seen or seen[-1] != phase):
            seen.append(phase)
    return seen


async def run_conversation(
    scenario_name: str,
    user_messages: Optional[List[str]] = None,
    max_turns: int = 30,
) -> Tuple[List[dict], dict]:
    """
    Run a single conversation with the orchestrator.
    If user_messages is provided, use those in order (and stop when exhausted).
    Otherwise use scenario initial_message and an LLM-simulated user that generates
    the next message each turn until phase is 'done' or max_turns (30) is reached.
    Returns (transcript, final_state_dict).
    """
    orchestrator = Orchestrator()
    transcript = []

    if user_messages is not None:
        # Fixed message list (manual override)
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
    else:
        # Simulated user: loop send user -> get agent -> generate next user until done or max_turns
        scenario = load_scenario(scenario_name)
        initial_message = scenario.get("initial_message", "I have a product idea.")
        if isinstance(initial_message, list):
            initial_message = initial_message[0] if initial_message else "I have a product idea."
        simulator = SimulatedUser(
            persona=scenario.get("persona", "You are a founder with a product idea."),
            message_policy=scenario.get("message_policy", "expansive"),
        )
        user_msg = initial_message
        for turn_i in range(max_turns):
            if turn_i > 0:
                await asyncio.sleep(TURN_DELAY_SECONDS)
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
            try:
                user_msg = await simulator.next_message(transcript)
            except Exception as e:
                transcript.append({"user": f"[SIM ERROR: {e}]", "assistant": "", "phase": state.phase})
                break
            if not user_msg:
                transcript.append({"user": "[SIMULATED USER RETURNED EMPTY]", "assistant": "", "phase": state.phase})
                break

    # Build state summary for scoring
    state = orchestrator.state
    state_dict = {
        "phase": state.phase,
        "reached_done": state.phase == "done",
        "turn_count": len(transcript),
        "phases_visited": _phases_visited(transcript),
        "discovery_summary": state.discovery_summary.model_dump() if state.discovery_summary else {},
        "scoping_output": state.scoping_output.model_dump() if state.scoping_output else None,
        "spec_length": len(state.spec_markdown or ""),
        "spec_markdown": state.spec_markdown or "",
        "negotiation_rounds": state.negotiation_rounds,
    }
    return transcript, state_dict


def format_transcript(transcript: List[dict]) -> str:
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

    for i, name in enumerate(scenario_names):
        if i > 0:
            print(f"(waiting {TURN_DELAY_SECONDS}s between scenarios for rate limits)\n")
            await asyncio.sleep(TURN_DELAY_SECONDS)
        print(f"=== Scenario: {name} ===\n")
        try:
            transcript, state_dict = await run_conversation(name)
            print(format_transcript(transcript))
            print(
                f"Final phase: {state_dict['phase']} | "
                f"reached_done: {state_dict['reached_done']} | "
                f"turns: {state_dict['turn_count']} | "
                f"phases: {state_dict['phases_visited']} | "
                f"spec length: {state_dict['spec_length']}"
            )
            saved = _save_transcript(name, transcript, state_dict)
            print(f"Transcript saved: {saved}\n")
            results = run_assertions(name, transcript, state_dict)
            print_checklist(name, results)
        except Exception as e:
            print(f"Error: {e}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
