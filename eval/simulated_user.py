"""LLM-as-User simulator for eval: roleplays founder from scenario persona and message_policy."""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

_DEBUG_LOG = Path("/Users/vinayakrastogi/Desktop/Agents/PM/.cursor/debug-31600c.log")

# Add project root so imports work
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from models.llm import llm_call


POLICY_INSTRUCTIONS = {
    "minimal": (
        "Reply with one or two words unless the PM explicitly asks for more. "
        "Only expand when the PM probes (e.g. 'can you be more specific?'). "
        "Stay in character as a founder who gives minimal answers."
    ),
    "expansive": (
        "Give full, detailed answers when asked. Accept scope proposals and summaries "
        "readily. Confirm quickly. Stay in character as a founder with a clear idea "
        "who is cooperative."
    ),
    "pushback": (
        "When the PM proposes cutting features, push back. Argue that certain features "
        "(e.g. social feed, admin panel) are core or essential. Want to see the agent "
        "evaluate your argument and either concede or hold firm. Stay in character."
    ),
    "pivot": (
        "Start with the initial idea. After about 3-4 exchanges, shift to a related but "
        "different idea (e.g. nutritionists instead of gym trainers, or B2B for gym owners). "
        "Stay in character as a founder who changes their mind mid-conversation."
    ),
}


def _build_system_prompt(persona: str, message_policy: str) -> str:
    policy = message_policy.strip().lower() if message_policy else "expansive"
    policy_instruction = POLICY_INSTRUCTIONS.get(
        policy, POLICY_INSTRUCTIONS["expansive"]
    )
    return (
        "You are roleplaying as a founder in a product discovery conversation with an AI PM. "
        "Your goal is to stay in character and respond as this founder would.\n\n"
        "PERSONA:\n"
        f"{persona.strip()}\n\n"
        "BEHAVIOR (message policy = {policy}):\n"
        f"{policy_instruction}\n\n"
        "Respond with ONLY the founder's next message—no labels, no meta-commentary. "
        "One short paragraph or a few sentences max unless the policy says to be very brief."
    ).format(policy=policy)


def _conversation_to_messages(conversation: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Turn transcript entries into LiteLLM message list for the simulated founder.

    Roles are from the simulator's perspective: the PM agent's replies are "user"
    (input) and the founder's prior messages are "assistant" (the simulator's own
    prior output).  This lets the LLM naturally continue generating as the founder.
    """
    messages = []
    for turn in conversation:
        messages.append({"role": "assistant", "content": turn["user"]})
        messages.append({"role": "user", "content": turn["assistant"]})
    return messages


class SimulatedUser:
    """
    Uses an LLM to generate the next founder message given scenario persona,
    message_policy, and conversation history.
    """

    def __init__(self, persona: str, message_policy: str = "expansive"):
        self.persona = persona or "You are a founder with a product idea."
        self.message_policy = message_policy or "expansive"
        self._system_prompt = _build_system_prompt(self.persona, self.message_policy)

    async def next_message(self, conversation: List[Dict[str, Any]]) -> str:
        """
        Generate the next user (founder) message given the conversation so far.
        conversation: list of {"user": str, "assistant": str, "phase": str}
        """
        if not conversation:
            raise ValueError("conversation must have at least one turn (user + assistant)")
        messages = [{"role": "system", "content": self._system_prompt}]
        messages.extend(_conversation_to_messages(conversation))
        # region agent log
        _DEBUG_LOG.open("a").write(json.dumps({"sessionId":"31600c","timestamp":int(time.time()*1000),"location":"simulated_user.py:next_message","message":"messages_to_llm","data":{"roles":[m["role"] for m in messages],"last_msg_role":messages[-1]["role"],"last_msg_content":messages[-1]["content"][:200],"num_messages":len(messages)},"hypothesisId":"A"}) + "\n")
        # endregion
        reply = await llm_call("extraction", messages)
        # region agent log
        _DEBUG_LOG.open("a").write(json.dumps({"sessionId":"31600c","timestamp":int(time.time()*1000),"location":"simulated_user.py:next_message","message":"raw_llm_reply","data":{"reply_repr":repr(reply)[:300],"reply_len":len(reply) if reply else 0,"stripped":repr((reply or "").strip())[:300]},"hypothesisId":"B"}) + "\n")
        # endregion
        return (reply or "").strip()
