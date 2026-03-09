"""Eval report generator: writes a timestamped markdown report after each full eval run."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Allow running from project root
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from eval.assertions import AssertionResult
from eval.rubric import RUBRIC_DIMENSIONS
from eval.judge import DIMENSION_LABELS, compute_overall, scores_to_row

REPORTS_DIR = Path(__file__).resolve().parent / "reports"
RESULTS_MD = Path(__file__).resolve().parent / "results.md"

# Ordered short column names for the comparison table
_TABLE_COLUMNS = list(DIMENSION_LABELS.values()) + ["overall"]


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y%m%d_%H%M%S")


def _ts_human(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _yesno(value) -> bool:
    return "Yes" if value else "No"


def _assertion_rows(results: List[AssertionResult]) -> str:
    lines = []
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        line = f"- [{mark}] `{r.name}`"
        if not r.passed and r.detail:
            line += f" — {r.detail}"
        lines.append(line)
    return "\n".join(lines)


def _model_metadata() -> str:
    """Return model routing info from config, with graceful fallback."""
    try:
        from config import MODELS
        parts = ", ".join(f"{k}={v}" for k, v in MODELS.items())
        return parts
    except Exception:
        return "unavailable"


# ---------------------------------------------------------------------------
# Layer 3 helpers
# ---------------------------------------------------------------------------

def _format_score_cell(entry: Optional[dict]) -> str:
    """Return 'N/5 — snippet' or 'N/A' for a single dimension."""
    if not entry:
        return "N/A"
    score = entry.get("score")
    if score is None:
        return "N/A"
    reasoning = entry.get("reasoning", "")
    snippet = reasoning[:100].rstrip()
    if len(reasoning) > 100:
        snippet += "..."
    return f"{score}/5 — \"{snippet}\""


def _judge_section(scenario_results: List[dict]) -> List[str]:
    """Render the Layer 3: LLM Judge Scores section."""
    lines: List[str] = [
        "## Layer 3: LLM Judge Scores",
        "",
        "> Scores are 1-5 per rubric dimension. `N/A` means the dimension was not tested.",
        "> Reasoning is truncated to 100 chars here; full reasoning in the JSON judge output.",
        "",
    ]

    for sr in scenario_results:
        name = sr["scenario"]
        scores = sr.get("judge_scores")
        error = sr.get("error")

        if error:
            lines.append(f"### {name}")
            lines.append("")
            lines.append(f"> **ERROR:** {error}")
            lines.append("")
            continue

        if scores is None:
            lines.append(f"### {name}")
            lines.append("")
            lines.append("> Judge not run for this scenario.")
            lines.append("")
            continue

        total, max_possible = compute_overall(scores)
        overall_str = f"{total}/{max_possible}" if max_possible > 0 else "N/A"
        lines.append(f"### {name} (Overall: {overall_str})")
        lines.append("")

        for dim in RUBRIC_DIMENSIONS:
            entry = scores.get(dim, {})
            label = DIMENSION_LABELS.get(dim, dim)
            formatted = _format_score_cell(entry)
            lines.append(f"- **{label}:** {formatted}")

        lines.append("")

    return lines


# ---------------------------------------------------------------------------
# Timestamped report
# ---------------------------------------------------------------------------

def generate_report(
    scenario_results: List[dict],
    run_timestamp: datetime,
    use_judge: bool = False,
) -> Path:
    """
    Write eval/reports/eval_{timestamp}.md and return the path.

    Each entry in scenario_results must have:
        scenario: str
        state_dict: dict
        assertions: List[AssertionResult]
        judge_scores: dict | None   (populated when use_judge=True)
        transcript_path: Path       (may be None if the scenario errored)
        error: str | None           (set if the scenario raised an exception)
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"eval_{_ts(run_timestamp)}.md"

    lines: List[str] = []

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------
    judge_note = " + LLM Judge" if use_judge else ""
    lines += [
        f"# Eval Report — {_ts_human(run_timestamp)}",
        "",
        "## Run Metadata",
        "",
        f"- **Models:** {_model_metadata()}",
        f"- **Eval layers:** Layer 2 (assertions){judge_note}",
        f"- **Scenarios run:** {len(scenario_results)}",
        f"- **Timestamp:** {_ts_human(run_timestamp)}",
        "",
    ]

    # -----------------------------------------------------------------------
    # Summary table
    # -----------------------------------------------------------------------
    if use_judge:
        header = "| Scenario | Assertions | Turns | Reached Done | Spec Length | Judge Overall | Transcript |"
        divider = "|---|---|---|---|---|---|---|"
    else:
        header = "| Scenario | Assertions | Turns | Reached Done | Spec Length | Transcript |"
        divider = "|---|---|---|---|---|---|"

    lines += ["## Summary", "", header, divider]

    total_passed = 0
    total_checks = 0

    for sr in scenario_results:
        name = sr["scenario"]
        error = sr.get("error")
        if error:
            if use_judge:
                lines.append(f"| {name} | ERROR | — | — | — | — | — |")
            else:
                lines.append(f"| {name} | ERROR | — | — | — | — |")
            continue

        state = sr.get("state_dict", {})
        assertions: List[AssertionResult] = sr.get("assertions", [])
        passed = sum(1 for a in assertions if a.passed)
        total = len(assertions)
        total_passed += passed
        total_checks += total

        turns = state.get("turn_count", "—")
        reached_done = _yesno(state.get("reached_done", False))
        spec_length = state.get("spec_length", 0)
        tp = sr.get("transcript_path")
        transcript_link = f"[transcript]({tp.name})" if tp else "—"

        if use_judge:
            scores = sr.get("judge_scores")
            if scores:
                tot, mx = compute_overall(scores)
                overall_str = f"{tot}/{mx}" if mx > 0 else "N/A"
            else:
                overall_str = "—"
            lines.append(
                f"| {name} | {passed}/{total} | {turns} | {reached_done} | {spec_length} | {overall_str} | {transcript_link} |"
            )
        else:
            lines.append(
                f"| {name} | {passed}/{total} | {turns} | {reached_done} | {spec_length} | {transcript_link} |"
            )

    if use_judge:
        lines.append(f"| **Total** | **{total_passed}/{total_checks}** | | | | | |")
    else:
        lines.append(f"| **Total** | **{total_passed}/{total_checks}** | | | | |")
    lines.append("")

    # -----------------------------------------------------------------------
    # Layer 2: Deterministic Assertions
    # -----------------------------------------------------------------------
    lines += [
        "## Layer 2: Deterministic Assertions",
        "",
        "> Programmatic pass/fail checks on transcript and final state.",
        "> Each check is either universal (all scenarios) or scenario-specific.",
        "",
    ]

    for sr in scenario_results:
        name = sr["scenario"]
        error = sr.get("error")
        assertions: List[AssertionResult] = sr.get("assertions", [])
        passed = sum(1 for a in assertions if a.passed)
        total = len(assertions)

        lines.append(f"### {name} ({passed}/{total} passed)")
        lines.append("")

        if error:
            lines.append(f"> **ERROR:** {error}")
        elif assertions:
            lines.append(_assertion_rows(assertions))
        else:
            lines.append("> No assertions recorded.")

        lines.append("")

    # -----------------------------------------------------------------------
    # Layer 3: LLM Judge Scores (only when judge was run)
    # -----------------------------------------------------------------------
    if use_judge:
        lines += _judge_section(scenario_results)
        lines += ["---", ""]
    else:
        lines += [
            "---",
            "",
            "*Layer 3 (LLM Judge) not run. Re-run with `--judge` to enable.*",
            "",
        ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# results.md — latest-run comparison table
# ---------------------------------------------------------------------------

def generate_results_md(
    scenario_results: List[dict],
    run_timestamp: datetime,
) -> Path:
    """
    Write (overwrite) eval/results.md with a cross-scenario comparison table.
    Called after a --judge run. Returns the path written.
    """
    lines: List[str] = [
        "# Eval Results — Latest Run",
        "",
        f"*Generated: {_ts_human(run_timestamp)}*  ",
        f"*Models: {_model_metadata()}*",
        "",
        "Columns: assertions pass rate + LLM judge scores (1-5) per dimension + overall.",
        "N/A = dimension not tested in that scenario.",
        "",
    ]

    # Table header
    col_headers = ["Scenario", "Assertions"] + [c.replace("_", " ") for c in _TABLE_COLUMNS]
    lines.append("| " + " | ".join(col_headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(col_headers)) + " |")

    for sr in scenario_results:
        name = sr["scenario"]
        error = sr.get("error")

        if error:
            row_cells = [name, "ERROR"] + ["—"] * len(_TABLE_COLUMNS)
            lines.append("| " + " | ".join(row_cells) + " |")
            continue

        assertions: List[AssertionResult] = sr.get("assertions", [])
        passed = sum(1 for a in assertions if a.passed)
        total = len(assertions)
        assertion_str = f"{passed}/{total}"

        scores = sr.get("judge_scores")
        score_row = scores_to_row(scores)  # {label: display_str}

        row_cells = (
            [name, assertion_str]
            + [score_row.get(col, "—") for col in _TABLE_COLUMNS]
        )
        lines.append("| " + " | ".join(row_cells) + " |")

    lines += [
        "",
        "---",
        "",
        "## Score Dimension Reference",
        "",
        "| Dimension | Column | What it measures |",
        "|---|---|---|",
    ]

    from eval.rubric import RUBRIC_DESCRIPTIONS
    for dim, label in DIMENSION_LABELS.items():
        desc = RUBRIC_DESCRIPTIONS.get(dim, "")
        # Truncate for table
        short_desc = desc[:120].rstrip()
        if len(desc) > 120:
            short_desc += "..."
        lines.append(f"| {dim} | {label} | {short_desc} |")

    lines += [
        "",
        "---",
        "",
        f"*Full per-scenario reports with detailed reasoning: [eval/reports/](reports/)*",
        "",
    ]

    RESULTS_MD.write_text("\n".join(lines), encoding="utf-8")
    return RESULTS_MD
