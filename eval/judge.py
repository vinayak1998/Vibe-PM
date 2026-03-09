"""Layer 3 eval: LLM-as-Judge. Scores a transcript against the rubric (1-5 per dimension)."""

import json
import sys
from pathlib import Path
from typing import Optional

# Add project root so imports work
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from eval.rubric import RUBRIC_DIMENSIONS, get_rubric_text
from models.llm import llm_call

# Abbreviated column headers used in summary tables
DIMENSION_LABELS = {
    "discovery_depth": "discovery",
    "conversation_naturalness": "naturalness",
    "scoping_quality": "scoping",
    "spec_accuracy": "spec",
    "argue_back_quality": "argue_back",
}

_SYSTEM_PROMPT = """\
You are an expert Product Manager evaluating an AI PM agent's conversation with a founder.

Your task is to score the agent's performance across 5 dimensions using the rubric provided.
Each dimension is scored 1-5. Score null if the dimension was not tested in this scenario.

CRITICAL RULES:
1. Provide your reasoning BEFORE giving the score for each dimension — think step by step.
2. Base scores strictly on what happened in the transcript, not on what could have happened.
3. If a dimension is not applicable (e.g. argue_back_quality for a scenario with no pushback),
   set score to null and reasoning to "N/A — scenario did not test this dimension".

Output ONLY valid JSON in this exact shape (no markdown, no prose outside JSON):
{
  "discovery_depth":          {"reasoning": "...", "score": 1-5 or null},
  "conversation_naturalness": {"reasoning": "...", "score": 1-5 or null},
  "scoping_quality":          {"reasoning": "...", "score": 1-5 or null},
  "spec_accuracy":            {"reasoning": "...", "score": 1-5 or null},
  "argue_back_quality":       {"reasoning": "...", "score": 1-5 or null}
}"""


def _build_user_message(
    transcript_text: str,
    scenario: dict,
    state_dict: dict,
    rubric: str,
) -> str:
    """Assemble the full user message for the judge: scenario → transcript → state → spec → rubric."""
    discovery = state_dict.get("discovery_summary") or {}
    discovery_filled = sum(1 for v in discovery.values() if v and str(v).strip())
    scoping = state_dict.get("scoping_output") or {}

    state_summary_lines = [
        f"- Phases visited: {state_dict.get('phases_visited', [])}",
        f"- Turn count: {state_dict.get('turn_count', 0)}",
        f"- Reached done: {state_dict.get('reached_done', False)}",
        f"- Negotiation rounds: {state_dict.get('negotiation_rounds', 0)}",
        f"- Discovery fields filled: {discovery_filled}/8",
        f"- Spec length (chars): {state_dict.get('spec_length', 0)}",
        f"- MVP features: {len(scoping.get('mvp_features') or [])}",
        f"- Cut features: {len(scoping.get('cut_features') or [])}",
    ]

    spec_section = ""
    spec_md = state_dict.get("spec_markdown", "")
    if spec_md and spec_md.strip():
        spec_section = f"\n\n## Final Spec (for spec_accuracy scoring)\n\n{spec_md}"

    parts = [
        f"## Scenario: {scenario.get('name', 'unknown')}",
        f"Description: {scenario.get('description', 'n/a')}",
        f"Persona: {scenario.get('persona', 'n/a').strip()}",
        "",
        "## Conversation Transcript",
        "",
        transcript_text,
        "",
        "## Final State Summary",
        "",
        "\n".join(state_summary_lines),
        spec_section,
        "",
        "## Scoring Rubric",
        "",
        rubric,
    ]
    return "\n".join(parts)


def _parse_judge_response(raw: str) -> dict:
    """Parse the LLM's JSON response. Raises ValueError on failure."""
    # Strip markdown fences if the model added them despite instructions
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop first and last fence lines
        inner = lines[1:] if lines[0].startswith("```") else lines
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner)
    return json.loads(text)


def _validate_scores(parsed: dict) -> dict:
    """Normalise and validate the parsed dict. Returns cleaned result."""
    result = {}
    for dim in RUBRIC_DIMENSIONS:
        entry = parsed.get(dim, {})
        if not isinstance(entry, dict):
            entry = {}
        reasoning = str(entry.get("reasoning") or "No reasoning provided.").strip()
        raw_score = entry.get("score")
        if raw_score is None:
            score = None
        else:
            try:
                score = int(raw_score)
                score = max(1, min(5, score))  # clamp to [1, 5]
            except (TypeError, ValueError):
                score = None
        result[dim] = {"reasoning": reasoning, "score": score}
    return result


async def judge_transcript(
    transcript_text: str,
    scenario: dict,
    state_dict: dict,
) -> dict:
    """
    Send the transcript + rubric to a 70B LLM and get 1-5 scores with reasoning.

    Returns:
        {
          "discovery_depth":          {"reasoning": str, "score": int | None},
          "conversation_naturalness": {"reasoning": str, "score": int | None},
          "scoping_quality":          {"reasoning": str, "score": int | None},
          "spec_accuracy":            {"reasoning": str, "score": int | None},
          "argue_back_quality":       {"reasoning": str, "score": int | None},
        }

    Raises on unrecoverable parse failure after one retry.
    """
    rubric = get_rubric_text()
    user_message = _build_user_message(transcript_text, scenario, state_dict, rubric)

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    # First attempt: ask for JSON object directly
    raw = await llm_call(
        "spec",
        messages,
        response_format={"type": "json_object"},
    )

    try:
        parsed = _parse_judge_response(raw)
        return _validate_scores(parsed)
    except (json.JSONDecodeError, ValueError):
        pass

    # Retry once with an explicit nudge
    nudge_messages = messages + [
        {"role": "assistant", "content": raw},
        {
            "role": "user",
            "content": (
                "Your response was not valid JSON. "
                "Respond ONLY with the JSON object as specified — no prose, no markdown fences."
            ),
        },
    ]
    raw2 = await llm_call(
        "spec",
        nudge_messages,
        response_format={"type": "json_object"},
    )
    parsed = _parse_judge_response(raw2)
    return _validate_scores(parsed)


def compute_overall(scores: dict) -> tuple[int, int]:
    """Return (total_score, max_possible) ignoring null dimensions."""
    total = 0
    max_possible = 0
    for dim in RUBRIC_DIMENSIONS:
        s = scores.get(dim, {}).get("score")
        if s is not None:
            total += s
            max_possible += 5
    return total, max_possible


def format_judge_scores(scores: dict) -> str:
    """Format judge scores as a readable console block."""
    lines = ["LLM Judge Scores:"]
    col_width = max(len(d) for d in RUBRIC_DIMENSIONS) + 1
    for dim in RUBRIC_DIMENSIONS:
        entry = scores.get(dim, {})
        score = entry.get("score")
        reasoning = entry.get("reasoning", "")
        # Truncate reasoning for console readability
        snippet = reasoning[:120].rstrip()
        if len(reasoning) > 120:
            snippet += "..."
        if score is None:
            score_str = "N/A"
        else:
            score_str = f"{score}/5"
        lines.append(f"  {dim:{col_width}s} {score_str:>4}  — \"{snippet}\"")
    total, max_possible = compute_overall(scores)
    lines.append(f"  Overall: {total}/{max_possible}")
    return "\n".join(lines)


def scores_to_row(scores: Optional[dict]) -> dict[str, str]:
    """Return a flat {column_label: display_string} dict for table rendering."""
    if not scores:
        return {label: "—" for label in DIMENSION_LABELS.values()}
    row = {}
    for dim, label in DIMENSION_LABELS.items():
        entry = scores.get(dim, {})
        score = entry.get("score")
        row[label] = "N/A" if score is None else f"{score}/5"
    total, max_possible = compute_overall(scores)
    row["overall"] = f"{total}/{max_possible}" if max_possible > 0 else "—"
    return row
