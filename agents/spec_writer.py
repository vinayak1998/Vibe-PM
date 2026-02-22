"""Spec Writer Agent: single-pass Markdown spec generation from discovery + scoping (phased)."""

from agents.base import BaseAgent
from models.schemas import ConversationState
from prompts.spec_writer import SPEC_WRITER_SYSTEM_PROMPT
from tools.templates import SPEC_TEMPLATE


def _phase_content(scope, phase_num: int) -> tuple[str, str, str, str, str, str]:
    """Build phase name, weeks, goal, features, flow, screens for phase_num (1/2/3)."""
    tbd = "TBD — needs further discovery."
    name = weeks = goal = features = flow = screens = tbd
    if not scope or not scope.implementation_phases:
        if scope and scope.mvp_features:
            phase_features = [f for f in scope.mvp_features if f.phase == phase_num]
            if phase_features:
                features = "\n".join(f"- {f.name}: {f.description}" for f in phase_features)
        return (f"Phase {phase_num}", "1-2 weeks", tbd, features or tbd, flow, screens)
    phases = {p.phase_number: p for p in scope.implementation_phases}
    p = phases.get(phase_num)
    if not p:
        if scope.mvp_features:
            phase_features = [f for f in scope.mvp_features if f.phase == phase_num]
            if phase_features:
                features = "\n".join(f"- {f.name}: {f.description}" for f in phase_features)
        return (f"Phase {phase_num}", "1-2 weeks", tbd, features or tbd, flow, screens)
    name = p.name
    weeks = p.estimated_weeks
    goal = p.goal or tbd
    phase_feature_names = set(p.features or [])
    phase_features = [f for f in scope.mvp_features if f.name in phase_feature_names or f.phase == phase_num]
    if not phase_features and p.features:
        features = "\n".join(f"- {fn}" for fn in p.features)
    else:
        features = "\n".join(f"- {f.name}: {f.description}" for f in phase_features) if phase_features else tbd
    if phase_num == 1 and scope.core_user_flow:
        flow = scope.core_user_flow
    if phase_num == 1 and scope.key_screens:
        screens = "\n".join(f"- {s}" for s in scope.key_screens)
    elif phase_num == 2 and scope.key_screens:
        screens = "\n".join(f"- {s}" for s in scope.key_screens[len(scope.key_screens) // 2 :])
    return (name, weeks, goal, features, flow, screens)


def _rice_summary(scope) -> str:
    """Build RICE summary from scoping output."""
    if not scope or not scope.mvp_features:
        return "TBD — needs further discovery."
    lines = []
    for f in scope.mvp_features:
        if f.rice_score is not None or f.rice_reach is not None:
            parts = [f.name]
            if f.rice_reach is not None:
                parts.append(f"Reach: {f.rice_reach}")
            if f.rice_impact is not None:
                parts.append(f"Impact: {f.rice_impact}")
            if f.rice_confidence is not None:
                parts.append(f"Confidence: {f.rice_confidence}")
            if f.rice_effort is not None:
                parts.append(f"Effort: {f.rice_effort} person-weeks")
            if f.rice_score is not None:
                parts.append(f"RICE score: {f.rice_score:.2f}")
            lines.append(" — ".join(parts))
    return "\n".join(lines) if lines else "TBD — needs further discovery."


class SpecWriterAgent(BaseAgent):
    """Generates a structured, phased product spec in Markdown. Single LLM call, not conversational."""

    async def handle_message(
        self, state: ConversationState, user_message: str
    ) -> tuple[str, ConversationState]:
        spec_md = await self._generate_spec(state)
        state.spec_markdown = spec_md
        state.phase = "done"
        state.messages.append(
            {"role": "assistant", "content": "Here's your product spec. You can download it below."}
        )
        return spec_md, state

    async def _generate_spec(self, state: ConversationState) -> str:
        """Single-pass generation: DiscoverySummary + ScopingOutput + template -> Markdown."""
        summary = state.discovery_summary
        scope = state.scoping_output

        context = self._build_context(summary, scope)
        messages = [
            {"role": "system", "content": SPEC_WRITER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Generate the full product spec following the template. Context:\n\n{context}\n\nOutput only the Markdown document, no commentary."},
        ]
        from models.llm import llm_call
        spec = await llm_call("spec", messages)
        if "# Product Spec:" not in spec and "# " not in spec:
            spec = self._fill_template_fallback(summary, scope, spec)
        return spec.strip()

    def _build_context(self, summary, scope) -> str:
        """Build context string for LLM from discovery + scoping (including phases and RICE)."""
        lines = [
            "## Discovery",
            f"Target user: {summary.target_user or 'TBD'}",
            f"Core problem: {summary.core_problem or 'TBD'}",
            f"Alternatives: {summary.current_alternatives}",
            f"Why now: {summary.why_now or 'TBD'}",
            f"Feature wishlist: {summary.feature_wishlist}",
            f"Success metric: {summary.success_metric or 'TBD'}",
            f"Revenue model: {summary.revenue_model or 'TBD'}",
            f"Constraints: {summary.constraints or 'TBD'}",
            "",
        ]
        if scope:
            lines.append("## Scoping")
            lines.append("MVP features (with phase and RICE when available):")
            for f in scope.mvp_features:
                rice = ""
                if f.rice_score is not None:
                    rice = f" [RICE: {f.rice_score:.2f}]"
                lines.append(f"  - [{f.priority}] Phase {f.phase}: {f.name}: {f.description}{rice}")
            lines.append("Cut features:")
            for c in scope.cut_features:
                lines.append(f"  - {c.name}: {c.reason_cut}")
            lines.append(f"Core user flow: {scope.core_user_flow or 'TBD'}")
            lines.append(f"Rationale: {scope.scope_rationale or 'TBD'}")
            if scope.key_screens:
                lines.append("Key screens:")
                for s in scope.key_screens:
                    lines.append(f"  - {s}")
            if scope.implementation_phases:
                lines.append("Implementation phases:")
                for p in scope.implementation_phases:
                    lines.append(f"  - Phase {p.phase_number}: {p.name} ({p.estimated_weeks}) — {p.goal}")
                    for fn in p.features:
                        lines.append(f"    - {fn}")
        lines.append("")
        lines.append("Template to follow:")
        lines.append(SPEC_TEMPLATE)
        return "\n".join(lines)

    def _fill_template_fallback(self, summary, scope, raw: str) -> str:
        """Fallback: fill phased template placeholders from discovery + scoping."""
        product_name = (summary.core_problem or "Product")[:50]
        problem_statement = summary.core_problem or "TBD — needs further discovery."
        target_user_persona = summary.target_user or "TBD — needs further discovery."
        cut_features = "TBD — needs further discovery."
        open_questions_risks = "TBD — needs further discovery."
        technical_considerations = "TBD — needs further discovery."
        comparable_products = "TBD — needs further discovery."

        p1_name, p1_weeks, p1_goal, p1_features, p1_flow, p1_screens = _phase_content(scope, 1)
        p2_name, p2_weeks, p2_goal, p2_features, p2_flow, p2_screens = _phase_content(scope, 2)
        p3_name, p3_weeks, p3_goal, p3_features, _, _ = _phase_content(scope, 3)

        if scope:
            cut_features = "\n".join(f"- {c.name}: {c.reason_cut}" for c in scope.cut_features) or cut_features
            comparable_products = "\n".join(f"- {c.name}: {c.relevance}" for c in scope.comparable_products) or comparable_products

        rice_summary = _rice_summary(scope)

        return SPEC_TEMPLATE.format(
            product_name=product_name,
            problem_statement=problem_statement,
            target_user_persona=target_user_persona,
            comparable_products=comparable_products,
            phase_1_name=p1_name,
            phase_1_weeks=p1_weeks,
            phase_1_goal=p1_goal,
            phase_1_features=p1_features,
            phase_1_flow=p1_flow,
            phase_1_screens=p1_screens,
            phase_2_name=p2_name,
            phase_2_weeks=p2_weeks,
            phase_2_goal=p2_goal,
            phase_2_features=p2_features,
            phase_2_screens=p2_screens,
            phase_3_name=p3_name,
            phase_3_weeks=p3_weeks,
            phase_3_goal=p3_goal,
            phase_3_features=p3_features,
            cut_features=cut_features,
            rice_summary=rice_summary,
            open_questions_risks=open_questions_risks,
            technical_considerations=technical_considerations,
        )
