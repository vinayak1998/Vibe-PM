"""Structured JSON extraction via Mistral."""

import json
import re
from typing import Optional

from models.llm import llm_call
from models.schemas import (
    DiscoverySummary,
    ScopingOutput,
    Feature,
    CutFeature,
    ComparableProduct,
    ImplementationPhase,
)
from prompts.extraction import EXTRACTION_DISCOVERY_PROMPT, EXTRACTION_SCOPING_PROMPT


def _extract_json_block(text: str) -> Optional[dict]:
    """Try to parse JSON from text (handle markdown code blocks). Returns dict only."""
    text = text.strip()
    # Strip optional markdown code block
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            text = match.group(1).strip()
    try:
        out = json.loads(text)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        return None


async def extract_discovery_summary(conversation_text: str) -> DiscoverySummary:
    """
    Extract/update DiscoverySummary from conversation using Mistral.
    On parse failure, returns empty DiscoverySummary (graceful degradation).
    """
    try:
        prompt = EXTRACTION_DISCOVERY_PROMPT.replace("{conversation}", conversation_text)
        raw = await llm_call("extraction", [{"role": "user", "content": prompt}])
        data = _extract_json_block(raw)
        if data is None:
            return DiscoverySummary()
        # Coerce to schema types so LLM oddities (e.g. list for string field) don't raise
        def _str(v):
            return str(v).strip() or None if v is not None and not isinstance(v, (list, dict)) else None

        def _str_list(v):
            if not isinstance(v, list):
                return []
            return [str(x) for x in v if x is not None]

        return DiscoverySummary(
            target_user=_str(data.get("target_user")),
            core_problem=_str(data.get("core_problem")),
            current_alternatives=_str_list(data.get("current_alternatives") or []),
            why_now=_str(data.get("why_now")),
            feature_wishlist=_str_list(data.get("feature_wishlist") or []),
            success_metric=_str(data.get("success_metric")),
            revenue_model=_str(data.get("revenue_model")),
            constraints=_str(data.get("constraints")),
        )
    except Exception:
        return DiscoverySummary()


async def extract_scoping_output(proposal_text: str) -> ScopingOutput:
    """
    Extract ScopingOutput from scoping proposal text using Mistral.
    On parse failure, returns empty ScopingOutput.
    """
    try:
        prompt = EXTRACTION_SCOPING_PROMPT.replace("{proposal}", proposal_text)
        raw = await llm_call("extraction", [{"role": "user", "content": prompt}])
        data = _extract_json_block(raw)
        if data is None:
            return ScopingOutput()
        mvp = []
        for f in data.get("mvp_features") or []:
            if isinstance(f, dict) and f.get("name") and f.get("priority") in ("P0", "P1", "P2"):
                phase = f.get("phase")
                if phase not in (1, 2, 3):
                    phase = 1
                mvp.append(
                    Feature(
                        name=str(f["name"]),
                        description=str(f.get("description", "")),
                        priority=f["priority"],
                        phase=int(phase) if phase is not None else 1,
                        rice_reach=int(f["rice_reach"]) if f.get("rice_reach") is not None else None,
                        rice_impact=float(f["rice_impact"]) if f.get("rice_impact") is not None else None,
                        rice_confidence=float(f["rice_confidence"]) if f.get("rice_confidence") is not None else None,
                        rice_effort=float(f["rice_effort"]) if f.get("rice_effort") is not None else None,
                        rice_score=float(f["rice_score"]) if f.get("rice_score") is not None else None,
                    )
                )
        cut = []
        for f in data.get("cut_features") or []:
            if isinstance(f, dict) and f.get("name"):
                cut.append(
                    CutFeature(name=str(f["name"]), reason_cut=str(f.get("reason_cut", "")))
                )
        comp = []
        for c in data.get("comparable_products") or []:
            if isinstance(c, dict) and c.get("name"):
                comp.append(
                    ComparableProduct(
                        name=str(c["name"]),
                        url=c.get("url"),
                        relevance=str(c.get("relevance", "")),
                    )
                )
        key_screens = []
        for s in data.get("key_screens") or []:
            if isinstance(s, str) and s.strip():
                key_screens.append(s.strip())
        impl_phases = []
        for p in data.get("implementation_phases") or []:
            if isinstance(p, dict) and p.get("phase_number") in (1, 2, 3) and p.get("name"):
                features = p.get("features") or []
                if not isinstance(features, list):
                    features = []
                impl_phases.append(
                    ImplementationPhase(
                        phase_number=int(p["phase_number"]),
                        name=str(p["name"]),
                        goal=str(p.get("goal", "")),
                        estimated_weeks=str(p.get("estimated_weeks", "1-2 weeks")),
                        features=[str(x) for x in features if x],
                    )
                )
        return ScopingOutput(
            mvp_features=mvp,
            cut_features=cut,
            comparable_products=comp,
            core_user_flow=data.get("core_user_flow"),
            scope_rationale=data.get("scope_rationale"),
            key_screens=key_screens,
            implementation_phases=impl_phases,
        )
    except Exception:
        return ScopingOutput()
