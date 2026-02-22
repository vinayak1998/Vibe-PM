"""Scoping Agent: opinionated PM with web search, MVP proposal, and argue-back loop."""

from agents.base import BaseAgent
from models.schemas import ComparableProduct, ConversationState, ScopingOutput
from prompts.scoping import SCOPING_SYSTEM_PROMPT
from tools.extraction import extract_scoping_output
from tools.intent import classify_scoping_intent
from tools.web_search import search_comparable_products


class ScopingAgent(BaseAgent):
    """
    On first entry (scoping_output is None): search comparables, generate MVP proposal, extract output.
    On subsequent messages: classify AGREE/PUSHBACK/QUESTION; if AGREE transition; if PUSHBACK do argue-back (max 3 rounds).
    """

    async def handle_message(
        self, state: ConversationState, user_message: str
    ) -> tuple[str, ConversationState]:
        # Initial proposal when entering scoping (no scoping_output yet)
        if state.scoping_output is None:
            return await self._generate_initial_proposal(state)

        # Classify intent
        intent = await classify_scoping_intent(user_message)
        if intent == "AGREE":
            state.scope_agreed = True
            state.awaiting_scope_agreement = False
            state.phase = "spec"
            reply = "Sounds good. I'll turn this into a product spec you can hand to a developer or code-gen tool."
            state.messages.append({"role": "assistant", "content": reply})
            return reply, state

        if intent == "QUESTION":
            # Answer clarifying question then re-ask for agreement
            conv = [{"role": m["role"], "content": m["content"]} for m in state.messages]
            conv.append({"role": "user", "content": user_message})
            reply = await self._llm_conversation(
                conv,
                SCOPING_SYSTEM_PROMPT
                + "\n\nThe user is asking a clarifying question about the scope. Answer briefly, then ask if they're ready to proceed with this scope.",
            )
            state.messages.append({"role": "user", "content": user_message})
            state.messages.append({"role": "assistant", "content": reply})
            return reply, state

        # PUSHBACK: argue-back loop
        state.messages.append({"role": "user", "content": user_message})
        state.negotiation_rounds += 1

        if state.negotiation_rounds >= state.max_negotiation_rounds:
            # Graceful concession
            reply = await self._llm_conversation(
                state.messages,
                SCOPING_SYSTEM_PROMPT
                + "\n\nYou've reached the max negotiation rounds. Gracefully concede: add or adjust what they asked for, flag the risk to scope/timeline, and say you're ready to move to the spec. Be brief.",
            )
            state.scope_agreed = True
            state.awaiting_scope_agreement = False
            state.phase = "spec"
            state.messages.append({"role": "assistant", "content": reply})
            return reply, state

        # Evaluate pushback: CONCEDE or HOLD_FIRM
        reply = await self._llm_conversation(
            state.messages,
            SCOPING_SYSTEM_PROMPT
            + "\n\nThe user is pushing back on your proposed scope. Evaluate their argument on: strength of argument, impact on scope, core-ness to value prop. Then either CONCEDE (add/change the feature and explain why) or HOLD_FIRM (explain why you're not changing). Reply in natural language only, no labels.",
        )
        state.messages.append({"role": "assistant", "content": reply})
        return reply, state

    async def _generate_initial_proposal(
        self, state: ConversationState
    ) -> tuple[str, ConversationState]:
        """Search comparables, generate MVP proposal, extract ScopingOutput."""
        summary = state.discovery_summary
        comparables = await search_comparable_products(summary)
        comp_text = "\n".join(
            f"- {r.get('title', '')}: {r.get('body', '')[:200]}..."
            if isinstance(r, dict)
            else str(r)[:200]
            for r in comparables[:5]
        )

        query = f"{summary.core_problem or 'product'} app for {summary.target_user or 'users'}"
        context = f"""
Discovery summary:
- Target user: {summary.target_user or 'TBD'}
- Core problem: {summary.core_problem or 'TBD'}
- Current alternatives: {summary.current_alternatives}
- Feature wishlist: {summary.feature_wishlist}
- Success metric: {summary.success_metric or 'TBD'}
- Constraints: {summary.constraints or 'TBD'}

Comparable products (from web search) — you MUST reference these in your reply:
{comp_text or 'None found.'}

Generate your MVP scope proposal. Start with: "Here's how I got here: I searched for [query], found [A, B, C], so I'm proposing …" Then explicitly reference the comparable products (e.g. "This sounds similar to X — what's different about your version?"). List P0/P1/P2 features, cut features with one-line reasons, the one core user flow and why it proves the idea, and 3-5 key screens (each: screen name + one-line description, derived from the core flow and P0 features). Then brief rationale. Be opinionated — cut aggressively. Social features, dashboards, and admin panels are never P0. Reply in natural language (no JSON). Then ask if they're ready to proceed or want to push back on anything.
"""
        messages_for_llm = [{"role": "user", "content": context}]
        reply = await self._llm_conversation(messages_for_llm, SCOPING_SYSTEM_PROMPT)
        state.messages.append({"role": "assistant", "content": reply})
        state.awaiting_scope_agreement = True

        # Extract structured output for spec writer later
        state.scoping_output = await extract_scoping_output(reply)

        # Merge actual search results into comparable_products so spec always has them
        existing_names = {c.name for c in state.scoping_output.comparable_products}
        existing_urls = {c.url for c in state.scoping_output.comparable_products if c.url}
        for r in comparables[:5]:
            if not isinstance(r, dict):
                continue
            name = (r.get("title") or "Unknown").strip() or "Unknown"
            url = r.get("href")
            relevance = (r.get("body") or "")[:300].strip() or "From web search"
            if name in existing_names or (url and url in existing_urls):
                continue
            state.scoping_output.comparable_products.append(
                ComparableProduct(name=name, url=url, relevance=relevance)
            )
            existing_names.add(name)
            if url:
                existing_urls.add(url)

        return reply, state
