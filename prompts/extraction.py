"""Prompts for structured extraction and intent classification (Mistral)."""

EXTRACTION_DISCOVERY_PROMPT = """Extract structured discovery information from the conversation below. Output valid JSON only, no other text. Use this exact schema — use null for missing fields and [] for empty lists:

{
  "target_user": string or null,
  "core_problem": string or null,
  "current_alternatives": list of strings,
  "why_now": string or null,
  "feature_wishlist": list of strings,
  "success_metric": string or null,
  "revenue_model": string or null,
  "constraints": string or null
}

Conversation:
---
{conversation}
---

JSON:"""

EXTRACTION_SCOPING_PROMPT = """Extract structured scoping output from the proposal below. Output valid JSON only, no other text. Use this exact schema:

{
  "mvp_features": [{"name": string, "description": string, "priority": "P0" or "P1" or "P2", "phase": 1 or 2 or 3, "rice_reach": number or null, "rice_impact": number or null, "rice_confidence": number or null, "rice_effort": number or null, "rice_score": number or null}],
  "cut_features": [{"name": string, "reason_cut": string}],
  "comparable_products": [{"name": string, "url": string or null, "relevance": string}],
  "core_user_flow": string or null,
  "scope_rationale": string or null,
  "key_screens": [string],
  "implementation_phases": [{"phase_number": 1 or 2 or 3, "name": string, "goal": string, "estimated_weeks": string, "features": [string]}]
}

key_screens: list of 3-5 strings, each a screen name and one-line description. Extract from the proposal; if none mentioned use [].
implementation_phases: list of 3 phases (Phase 1: Core MVP, Phase 2: Essential Additions, Phase 3: Growth & Polish). Each has phase_number, name, goal, estimated_weeks (e.g. "1-2 weeks"), and features (list of feature names). If not clearly stated, infer from the proposal.
mvp_features: include phase (1/2/3) and RICE fields when present; use null for missing RICE values.

Proposal text:
---
{proposal}
---

JSON:"""

CLASSIFY_DISCOVERY_REVIEW_PROMPT = """The PM just showed the user a discovery summary and asked: "Does this capture everything correctly? If so, I'll hand this off to scoping."

Did the user confirm they are happy with the summary and ready to move on (e.g. "yes", "sounds good", "that's right", "looks good", "let's go", "ok")? Or do they want to revise something (e.g. "actually...", "can we change...", "I'd add...")?

Reply with exactly one word: CONFIRM or REVISE.

User response:
---
{user_response}
---

One word:"""

CLASSIFY_SCOPING_INTENT_PROMPT = """Classify the user's response to the PM's proposed MVP scope.

Reply with exactly one word:
- AGREE: user agrees to the scope (e.g. "sounds good", "let's do it", "ok", "that works")
- PUSHBACK: user disagrees or wants to add/change something (e.g. "I need X", "don't cut Y", "what about Z")
- QUESTION: user is asking a clarifying question, not agreeing or pushing back

User response:
---
{user_response}
---

One word:"""
