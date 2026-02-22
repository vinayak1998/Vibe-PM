"""Discovery Agent: PM-style interviewer with extraction and completeness checkpoint."""

from config import DISCOVERY_MIN_TURNS
from agents.base import BaseAgent
from models.schemas import ConversationState, DiscoverySummary
from prompts.discovery import (
    DISCOVERY_ASK_FOR_IDEA_PROMPT,
    DISCOVERY_SUMMARY_PROMPT,
    DISCOVERY_SYSTEM_PROMPT,
)
from tools.completeness import check_completeness
from tools.extraction import extract_discovery_summary
from tools.intent import classify_discovery_review


# Human-readable labels for gap injection (no longer in config)
GAP_LABELS = {
    "target_user": "target user / persona",
    "core_problem": "core problem / pain points",
    "current_alternatives": "current alternatives",
    "why_now": "why now",
    "feature_wishlist": "feature vision / wishlist",
    "success_metric": "success metric",
    "revenue_model": "revenue model",
    "constraints": "constraints",
}


def _build_prompt(state: ConversationState) -> str:
    """Build system prompt: ask-for-idea on first message, else main SOP + gaps."""
    user_msgs = [m for m in state.messages if m.get("role") == "user"]
    if len(user_msgs) == 1 and len(state.messages) == 1:
        return DISCOVERY_ASK_FOR_IDEA_PROMPT

    parts = [DISCOVERY_SYSTEM_PROMPT]
    score, gaps, _ = check_completeness(state.discovery_summary)
    if gaps:
        parts.append("\n\n--- Gaps remaining (probe these naturally) ---")
        for g in gaps:
            label = GAP_LABELS.get(g, g)
            parts.append(f"- {label}: not yet discussed")
    return "\n".join(parts)


def _is_structured_output(reply: str) -> bool:
    """True if reply looks like a document/table instead of conversation."""
    if not reply or len(reply) < 20:
        return False
    r = reply.strip()
    if "|---" in r or "| ---" in r:
        return True
    if r.startswith("# ") and any(
        h in r[:200] for h in ("Product Requirements", "PRD", "Feature", "Executive Summary")
    ):
        return True
    return False


async def _merge_extracted_into_summary(state: ConversationState, conv_text: str) -> None:
    """Extract from conversation and merge into state.discovery_summary."""
    extracted = await extract_discovery_summary(conv_text)
    merged = state.discovery_summary.model_dump()
    for k, v in extracted.model_dump().items():
        if v is not None and v != [] and v != "":
            merged[k] = v
    str_fields = {"target_user", "core_problem", "why_now", "success_metric", "revenue_model", "constraints"}
    list_fields = {"current_alternatives", "feature_wishlist"}
    for f in str_fields:
        val = merged.get(f)
        if val is not None and not isinstance(val, str):
            merged[f] = str(val).strip() or None
    for f in list_fields:
        val = merged.get(f)
        if not isinstance(val, list):
            merged[f] = []
        else:
            merged[f] = [str(x) for x in val if x is not None]
    state.discovery_summary = DiscoverySummary(**merged)


class DiscoveryAgent(BaseAgent):
    """
    Conducts discovery interview. Checkpoint-based: extract after each turn,
    check_completeness; when complete (and min turns), show summary for user
    confirmation. No per-aspect state machine. Output validation rejects
    structured output (tables, PRDs).
    """

    async def handle_message(
        self, state: ConversationState, user_message: str
    ) -> tuple[str, ConversationState]:
        state.messages.append({"role": "user", "content": user_message})

        # Already showed summary — user is responding; check if they confirmed
        if state.discovery_summary_shown:
            confirmed = await classify_discovery_review(user_message)
            if confirmed:
                state.phase = "scoping"
                msg = "Great, I'm handing off to the Scoping Agent now."
                state.messages.append({"role": "assistant", "content": msg})
                return msg, state
            state.discovery_summary_shown = False

        # Extract and merge into summary
        conv_text = "\n".join(f"{m['role']}: {m['content']}" for m in state.messages)
        await _merge_extracted_into_summary(state, conv_text)

        # Completeness check (only after minimum turns)
        turn_count = sum(1 for m in state.messages if m.get("role") == "user")
        if turn_count >= DISCOVERY_MIN_TURNS:
            score, gaps, is_complete = check_completeness(state.discovery_summary)
            if is_complete:
                summary_reply = await self._generate_summary(state)
                state.discovery_summary_shown = True
                state.messages.append({"role": "assistant", "content": summary_reply})
                return summary_reply, state

        # Normal conversation turn
        system = _build_prompt(state)
        conv = [{"role": m["role"], "content": m["content"]} for m in state.messages]
        reply = await self._llm_conversation(conv, system)

        if _is_structured_output(reply):
            reply = await self._retry_conversational(conv, system)

        state.messages.append({"role": "assistant", "content": reply})
        return reply, state

    async def _generate_summary(self, state: ConversationState) -> str:
        """Generate discovery summary for user confirmation (handoff prep)."""
        conv_text = "\n".join(f"{m['role']}: {m['content']}" for m in state.messages)
        messages = [
            {"role": "user", "content": f"Conversation:\n\n{conv_text}\n\nGenerate the summary as specified in the system prompt."}
        ]
        return await self._llm_conversation(messages, DISCOVERY_SUMMARY_PROMPT)

    async def _retry_conversational(self, conv: list[dict], system: str) -> str:
        """Retry with corrective prompt when LLM produced structured output."""
        corrective = (
            "\n\nIMPORTANT: Reply only in natural conversation. "
            "Do NOT output tables, feature lists, or PRD-style documents. "
            "One short paragraph and one question max."
        )
        return await self._llm_conversation(conv, system + corrective)
